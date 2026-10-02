from __future__ import annotations

from decimal import Decimal

import pytest

from src.core.errors import DomainError
from src.services.registry import validate_snapshot
from src.services.rule_engine import RuleInterpreter
from src.services.scoring_engine import _match_norm, score_snapshot, validate_answers
from tests.conftest import SYNTH_BALANCE_DEMO


@pytest.mark.parametrize(
    ("answers", "aggregate", "display", "band"),
    [
        ({"q1": 2, "q2": 3, "q3": 1, "q4": 0}, "6", "5.00", "demo_middle"),
        ({"q1": 0, "q2": 0, "q3": 0, "q4": 0}, "6", "5.00", "demo_middle"),
        (
            {"q1": 3, "q3": 1, "q4": 0},
            "9.333333333333333333333333333",
            "7.78",
            "demo_upper",
        ),
    ],
)
def test_contract_scoring_vectors(answers, aggregate, display, band):
    result = score_snapshot(SYNTH_BALANCE_DEMO, answers, "full")
    scale = result["scales"][0]
    assert scale["aggregate_score_unrounded"].startswith(aggregate.rstrip("3"))
    assert scale["score_display"] == display
    assert scale["norm_band_code"] == band


def test_insufficient_data_skips_score_norm_and_interpretation():
    scale = score_snapshot(SYNTH_BALANCE_DEMO, {"q1": 3, "q2": 0}, "full")["scales"][0]
    assert scale["validity_status"] == "insufficient_data"
    assert scale["score_display"] is None
    assert scale["norm_band_code"] is None
    assert scale["interpretation_code"] is None


@pytest.mark.parametrize(
    ("answers", "code"),
    [
        ({"q2": 4}, "VALUE_OUT_OF_RANGE"),
        ({"q2": "3.0"}, "TYPE_INVALID"),
        ({"unknown": 1}, "UNKNOWN_ITEM"),
    ],
)
def test_response_validation_codes(answers, code):
    assert code in {
        issue["error_code"] for issue in validate_answers(SYNTH_BALANCE_DEMO, answers)
    }


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        ("3.333333", "demo_middle"),
        ("6.666667", "demo_upper"),
        ("6.6666666", "demo_middle"),
    ],
)
def test_norm_uses_unrounded_boundaries(score, expected):
    assert (
        _match_norm(SYNTH_BALANCE_DEMO["norm"], Decimal(score))["band_code"] == expected
    )


def test_rule_rounding_is_half_up():
    value = RuleInterpreter().evaluate(
        {
            "op": "round",
            "value": {"op": "const", "value": "2.345"},
            "decimals": 2,
            "mode": "half_up",
        },
        {},
    )
    assert value == Decimal("2.35")


@pytest.mark.parametrize("operator", ["eval", "exec", "import", "unknown"])
def test_arbitrary_code_operators_are_rejected(operator):
    with pytest.raises(DomainError) as caught:
        RuleInterpreter().validate({"op": operator, "value": "x"})
    assert caught.value.code == "RULE_SCHEMA_INVALID"


def test_rule_depth_limit():
    node = {"op": "const", "value": "1"}
    for _ in range(21):
        node = {"op": "abs", "value": node}
    with pytest.raises(DomainError) as caught:
        RuleInterpreter().validate(node)
    assert caught.value.code == "RULE_LIMIT_EXCEEDED"


def test_rule_args_limit():
    node = {"op": "add", "args": [{"op": "const", "value": "1"}] * 101}
    with pytest.raises(DomainError) as caught:
        RuleInterpreter().validate(node)
    assert caught.value.code == "RULE_SCHEMA_INVALID"


def test_division_by_zero_has_stable_code():
    node = {
        "op": "div",
        "left": {"op": "const", "value": "1"},
        "right": {"op": "const", "value": "0"},
    }
    with pytest.raises(DomainError) as caught:
        RuleInterpreter().evaluate(node, {})
    assert caught.value.code == "DIVISION_BY_ZERO"


def test_summary_disclosure_removes_item_values():
    result = score_snapshot(
        SYNTH_BALANCE_DEMO, {"q1": 2, "q2": 3, "q3": 1, "q4": 0}, "summary_only"
    )
    assert all(
        step["entity_ref"] is None or step["entity_ref"].get("kind") != "item"
        for step in result["trace"]
    )


def test_norm_overlap_is_rejected_at_publish_validation():
    snapshot = {**SYNTH_BALANCE_DEMO, "norm": {**SYNTH_BALANCE_DEMO["norm"]}}
    snapshot["norm"]["bands"] = [
        {
            "band_code": "a",
            "lower_bound": "0",
            "lower_inclusive": True,
            "upper_bound": "5",
            "upper_inclusive": True,
        },
        {
            "band_code": "b",
            "lower_bound": "5",
            "lower_inclusive": True,
            "upper_bound": "10",
            "upper_inclusive": True,
        },
    ]
    with pytest.raises(DomainError) as caught:
        validate_snapshot(snapshot, "uz-Latn")
    assert caught.value.code == "NORM_OVERLAP"
