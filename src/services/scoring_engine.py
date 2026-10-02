from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Any

from src.core.errors import DomainError
from src.services.rule_engine import RuleInterpreter, decimal_text, decimal_value

DISCLAIMER = "Bu natija tibbiy tashxis emas."


def validate_answers(snapshot: dict, answers: dict[str, Any]) -> list[dict[str, Any]]:
    items = {item["item_code"]: item for item in snapshot.get("items", [])}
    issues: list[dict[str, Any]] = []
    for code in answers:
        if code not in items:
            issues.append(
                {"item_code": code, "error_code": "UNKNOWN_ITEM", "safe_params": {}}
            )
    for code, item in items.items():
        value = answers.get(code)
        if value is None:
            if item.get("required", True):
                issues.append(
                    {
                        "item_code": code,
                        "error_code": "ITEM_REQUIRED",
                        "safe_params": {},
                    }
                )
            continue
        kind = item["item_type"]
        constraints = item.get("value_constraints", {})
        if kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                issues.append(
                    {"item_code": code, "error_code": "TYPE_INVALID", "safe_params": {}}
                )
                continue
            numeric = Decimal(value)
        elif kind == "decimal":
            try:
                numeric = decimal_value(value)
            except DomainError:
                issues.append(
                    {"item_code": code, "error_code": "TYPE_INVALID", "safe_params": {}}
                )
                continue
        elif kind == "boolean":
            if not isinstance(value, bool):
                issues.append(
                    {
                        "item_code": code,
                        "error_code": "BOOLEAN_LITERAL_INVALID",
                        "safe_params": {},
                    }
                )
            continue
        elif kind == "single_choice":
            options = {option["option_code"] for option in item.get("options", [])}
            if not isinstance(value, str) or value not in options:
                issues.append(
                    {
                        "item_code": code,
                        "error_code": "OPTION_NOT_ALLOWED",
                        "safe_params": {"allowed_option_codes": sorted(options)},
                    }
                )
            continue
        else:
            issues.append(
                {"item_code": code, "error_code": "TYPE_INVALID", "safe_params": {}}
            )
            continue
        if (
            "min" in constraints
            and numeric < Decimal(str(constraints["min"]))
            or "max" in constraints
            and numeric > Decimal(str(constraints["max"]))
        ):
            issues.append(
                {
                    "item_code": code,
                    "error_code": "VALUE_OUT_OF_RANGE",
                    "safe_params": {},
                }
            )
            continue
        if "step" in constraints:
            minimum = Decimal(str(constraints.get("min", 0)))
            step = Decimal(str(constraints["step"]))
            if step <= 0 or (numeric - minimum) % step != 0:
                issues.append(
                    {"item_code": code, "error_code": "STEP_INVALID", "safe_params": {}}
                )
    return issues


def score_snapshot(
    snapshot: dict, answers: dict[str, Any], disclosure: str
) -> dict[str, Any]:
    issues = validate_answers(snapshot, answers)
    if issues:
        raise DomainError(
            "RESPONSE_NOT_VALIDATED", "Response contains validation errors"
        )
    interpreter = RuleInterpreter()
    item_scores: dict[str, Decimal | None] = {}
    trace: list[dict[str, Any]] = [
        {
            "step_code": "execution_gate",
            "status": "completed",
            "outputs": [{"name": "gate", "value": "passed"}],
        },
        {
            "step_code": "response_validation",
            "status": "completed",
            "outputs": [{"name": "issues", "value": 0}],
        },
    ]
    for item in snapshot["items"]:
        code = item["item_code"]
        value = answers.get(code)
        if value is None:
            item_scores[code] = None
            if disclosure != "summary_only":
                trace.append(
                    {
                        "step_code": "missing_check",
                        "status": "completed",
                        "entity_ref": {"kind": "item", "code": code},
                        "outputs": [{"name": "missing", "value": True}],
                    }
                )
            continue
        raw = _map_score(item, value)
        if disclosure != "summary_only":
            mapping_inputs = (
                [] if disclosure != "full" else [{"name": "answer", "value": value}]
            )
            trace.append(
                {
                    "step_code": "option_mapping",
                    "status": "completed",
                    "entity_ref": {"kind": "item", "code": code},
                    "inputs": mapping_inputs,
                    "outputs": [{"name": "raw_score", "value": decimal_text(raw)}],
                    "redactions": [] if disclosure == "full" else ["raw_answer"],
                }
            )
        reverse = item.get("reverse_scoring", {"mode": "none"})
        transformed = raw
        if reverse.get("mode", "none") == "range":
            transformed = (
                decimal_value(reverse["min_score"])
                + decimal_value(reverse["max_score"])
                - raw
            )
        elif reverse.get("mode") == "explicit_map":
            mapping = reverse.get("map", {})
            key = decimal_text(raw)
            if key not in mapping:
                raise DomainError("MAPPING_NOT_FOUND", "Reverse mapping is incomplete")
            transformed = decimal_value(mapping[key])
        if disclosure != "summary_only":
            trace.append(
                {
                    "step_code": "item_reverse",
                    "status": "completed",
                    "entity_ref": {"kind": "item", "code": code},
                    "rule_ref": reverse.get("mode", "none"),
                    "outputs": [
                        {"name": "reversed_score", "value": decimal_text(transformed)}
                    ],
                }
            )
        if item.get("item_transform_expr"):
            transformed = interpreter.evaluate(
                item["item_transform_expr"],
                {
                    f"item_raw_score:{code}": raw,
                    f"item_reversed_score:{code}": transformed,
                },
            )
        item_scores[code] = transformed

    scale_outputs: list[dict[str, Any]] = []
    for scale in snapshot["scales"]:
        codes = scale.get("item_codes") or [
            item["item_code"] for item in snapshot["items"]
        ]
        values = [item_scores.get(code) for code in codes]
        answered = [value for value in values if value is not None]
        answered_count, missing_count = len(answered), len(values) - len(answered)
        aggregation = scale["aggregation"]
        if answered_count < aggregation.get(
            "min_answered", len(values)
        ) or missing_count > aggregation.get("max_missing", 0):
            scale_outputs.append(
                {
                    "scale_code": scale["scale_code"],
                    "validity_status": "insufficient_data",
                    "reason_codes": ["INSUFFICIENT_DATA"],
                    "answered_count": answered_count,
                    "missing_count": missing_count,
                    "aggregate_score_unrounded": None,
                    "score_unrounded": None,
                    "score_display": None,
                    "unit_code": scale["unit_code"],
                    "norm_band_code": None,
                    "normalized_value": None,
                    "interpretation_code": None,
                    "interpretation_snapshot_i18n": None,
                    "disclosure_level_applied": disclosure,
                }
            )
            trace.append(
                {
                    "step_code": "scale_aggregate",
                    "status": "skipped",
                    "entity_ref": {"kind": "scale", "code": scale["scale_code"]},
                    "reason_code": "INSUFFICIENT_DATA",
                    "outputs": [
                        {"name": "answered_count", "value": answered_count},
                        {"name": "missing_count", "value": missing_count},
                    ],
                }
            )
            continue
        with localcontext() as ctx:
            ctx.prec = 28
            aggregate = _aggregate(aggregation, answered, codes, item_scores, scale)
            score = aggregate
            if scale.get("transform_expr"):
                score = interpreter.evaluate(
                    scale["transform_expr"],
                    {f"aggregate:{scale['scale_code']}": aggregate},
                )
        if score < decimal_value(scale["theoretical_min"]) or score > decimal_value(
            scale["theoretical_max"]
        ):
            raise DomainError(
                "SCORE_OUT_OF_RANGE", "Scale score is outside its declared range"
            )
        norm = scale.get("norm") or snapshot.get("norm")
        band = _match_norm(norm, score) if norm else None
        interpretation = _interpret(
            snapshot.get("interpretations", []), scale, score, band, interpreter
        )
        reason_codes = [] if interpretation else ["NO_INTERPRETATION_MATCH"]
        quantum = Decimal(1).scaleb(-scale.get("display_decimals", 2))
        display = format(
            score.quantize(quantum, rounding=ROUND_HALF_UP),
            f".{scale.get('display_decimals', 2)}f",
        )
        scale_outputs.append(
            {
                "scale_code": scale["scale_code"],
                "validity_status": "valid",
                "reason_codes": reason_codes,
                "answered_count": answered_count,
                "missing_count": missing_count,
                "aggregate_score_unrounded": decimal_text(aggregate),
                "score_unrounded": decimal_text(score),
                "score_display": display,
                "unit_code": scale["unit_code"],
                "norm_band_code": band.get("band_code") if band else None,
                "normalized_value": band.get("normalized_value") if band else None,
                "interpretation_code": (
                    interpretation.get("interpretation_code")
                    if interpretation
                    else None
                ),
                "interpretation_snapshot_i18n": (
                    interpretation.get("text_i18n") if interpretation else None
                ),
                "disclosure_level_applied": disclosure,
            }
        )
        trace.extend(
            [
                {
                    "step_code": "scale_aggregate",
                    "status": "completed",
                    "entity_ref": {"kind": "scale", "code": scale["scale_code"]},
                    "outputs": [
                        {
                            "name": "aggregate_score_unrounded",
                            "value": decimal_text(aggregate),
                        },
                        {"name": "answered_count", "value": answered_count},
                        {"name": "missing_count", "value": missing_count},
                    ],
                },
                {
                    "step_code": "scale_transform",
                    "status": "completed",
                    "entity_ref": {"kind": "scale", "code": scale["scale_code"]},
                    "outputs": [
                        {"name": "score_unrounded", "value": decimal_text(score)}
                    ],
                },
                {
                    "step_code": "norm_match",
                    "status": "completed" if band else "skipped",
                    "reason_code": None if band else "NO_NORM_MATCH",
                    "outputs": [
                        {
                            "name": "norm_band_code",
                            "value": band.get("band_code") if band else None,
                        }
                    ],
                },
                {
                    "step_code": "interpretation_select",
                    "status": "completed" if interpretation else "skipped",
                    "reason_code": (
                        None if interpretation else "NO_INTERPRETATION_MATCH"
                    ),
                    "outputs": [
                        {
                            "name": "interpretation_code",
                            "value": (
                                interpretation.get("interpretation_code")
                                if interpretation
                                else None
                            ),
                        }
                    ],
                },
                {
                    "step_code": "round_display",
                    "status": "completed",
                    "inputs": [
                        {"name": "score_unrounded", "value": decimal_text(score)}
                    ],
                    "outputs": [{"name": "score_display", "value": display}],
                },
            ]
        )
    for sequence, step in enumerate(trace, 1):
        step["sequence"] = sequence
        step.setdefault("inputs", [])
        step.setdefault("outputs", [])
        step.setdefault("entity_ref", None)
        step.setdefault("rule_ref", None)
        step.setdefault("reason_code", None)
        step.setdefault("redactions", [])
        step["message_key"] = f"trace.{step['step_code']}"
    status = (
        "complete"
        if all(
            not scale["reason_codes"]
            for scale in scale_outputs
            if scale["validity_status"] == "valid"
        )
        else "complete_with_uninterpreted_scales"
    )
    return {"status": status, "scales": scale_outputs, "trace": trace}


def _map_score(item: dict, value: Any) -> Decimal:
    if item["item_type"] == "single_choice":
        option = next(
            (
                entry
                for entry in item.get("options", [])
                if entry["option_code"] == value
            ),
            None,
        )
        if not option:
            raise DomainError("MAPPING_NOT_FOUND", "Response option is not mapped")
        return decimal_value(option["score_value"])
    if item["item_type"] == "boolean":
        mapping = item.get("score_mapping", {}).get("map", {})
        key = "true" if value else "false"
        if key not in mapping:
            raise DomainError("MAPPING_NOT_FOUND", "Boolean mapping is incomplete")
        return decimal_value(mapping[key])
    return Decimal(value) if isinstance(value, int) else decimal_value(value)


def _aggregate(
    config: dict,
    answered: list[Decimal],
    codes: list[str],
    scores: dict[str, Decimal | None],
    scale: dict,
) -> Decimal:
    op = config["op"]
    if op == "sum":
        return sum(answered, Decimal(0))
    if op == "mean":
        return sum(answered, Decimal(0)) / len(answered)
    if op == "sum_prorated":
        return (
            sum(answered, Decimal(0))
            / len(answered)
            * Decimal(config["target_item_count"])
        )
    if op == "weighted_sum":
        weights = scale.get("weights", {})
        total = Decimal(0)
        for code in codes:
            score = scores.get(code)
            if score is not None:
                total += score * decimal_value(weights.get(code, "1"))
        return total
    raise DomainError("RULE_SCHEMA_INVALID", "Aggregation operator is not allowed")


def _match_norm(norm: dict, score: Decimal) -> dict | None:
    matches = []
    for band in norm.get("bands", []):
        lower = band.get("lower_bound")
        upper = band.get("upper_bound")
        lower_ok = (
            lower is None
            or score > decimal_value(lower)
            or band.get("lower_inclusive", False)
            and score == decimal_value(lower)
        )
        upper_ok = (
            upper is None
            or score < decimal_value(upper)
            or band.get("upper_inclusive", False)
            and score == decimal_value(upper)
        )
        if lower_ok and upper_ok:
            matches.append(band)
    if len(matches) > 1:
        raise DomainError("NORM_OVERLAP", "More than one norm band matched")
    return matches[0] if matches else None


def _interpret(
    rules: list[dict],
    scale: dict,
    score: Decimal,
    band: dict | None,
    interpreter: RuleInterpreter,
) -> dict | None:
    context = {
        f"transformed_score:{scale['scale_code']}": score,
        f"norm_band_code:{scale['scale_code']}": (
            band.get("band_code") if band else None
        ),
        f"normalized_value:{scale['scale_code']}": (
            decimal_value(band["normalized_value"])
            if band and band.get("normalized_value")
            else None
        ),
        f"validity_status:{scale['scale_code']}": "valid",
    }
    candidates = sorted(
        (
            rule
            for rule in rules
            if rule.get("scale_code", scale["scale_code"]) == scale["scale_code"]
        ),
        key=lambda rule: rule.get("priority", 10000),
    )
    for rule in candidates:
        if interpreter.evaluate(rule["when"], context):
            return rule
    return None
