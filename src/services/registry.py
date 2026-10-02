from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import DomainError
from src.models.domain import (
    InterpretationRule,
    Item,
    LicenceRevision,
    Methodology,
    MethodologyVersion,
    NormBand,
    NormSet,
    ResponseOption,
    Scale,
    ScaleItemLink,
)
from src.schemas.api import LicenceCreate, MethodologyCreate, MethodologyVersionCreate
from src.services.audit import audit
from src.services.rule_engine import RuleInterpreter, decimal_value


def canonical_hash(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def create_methodology(
    db: Session, payload: MethodologyCreate, actor_id: str
) -> Methodology:
    if db.scalar(
        select(Methodology).where(
            Methodology.methodology_code == payload.methodology_code
        )
    ):
        raise DomainError(
            "METHODOLOGY_CODE_EXISTS", "Methodology code already exists", 409
        )
    methodology = Methodology(**payload.model_dump(), created_by=actor_id)
    db.add(methodology)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        action="methodology.create",
        object_type="methodology",
        object_id=methodology.id,
    )
    return methodology


SCALE_KINDS = {"total", "factor", "subscale"}


def validate_snapshot(snapshot: dict, default_locale: str) -> None:
    items = snapshot.get("items")
    scales = snapshot.get("scales")
    if (
        not isinstance(items, list)
        or not items
        or not isinstance(scales, list)
        or not scales
    ):
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID", "Snapshot requires non-empty items and scales"
        )
    item_codes = [item.get("item_code") for item in items]
    scale_codes = [scale.get("scale_code") for scale in scales]
    if None in item_codes or len(set(item_codes)) != len(item_codes):
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID", "Item codes must be present and unique"
        )
    if None in scale_codes or len(set(scale_codes)) != len(scale_codes):
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID", "Scale codes must be present and unique"
        )
    kinds = [scale.get("scale_kind") for scale in scales]
    if any(kind not in SCALE_KINDS for kind in kinds):
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID",
            "Scale kind must be one of: " + ", ".join(sorted(SCALE_KINDS)),
        )
    # A total score is optional: multi-factor instruments such as the Big Five report
    # several primary factors, and a sum across them would be an invented score.
    if kinds.count("total") > 1:
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID", "Snapshot allows at most one total scale"
        )
    if "total" not in kinds and "factor" not in kinds:
        raise DomainError(
            "METHODOLOGY_SCHEMA_INVALID",
            "Snapshot requires a total scale or at least one factor scale",
        )
    known_items = set(item_codes)
    for scale in scales:
        unknown = set(scale.get("item_codes") or []) - known_items
        if unknown:
            raise DomainError(
                "METHODOLOGY_SCHEMA_INVALID",
                "Scale refers to unknown items",
                details={"scale_code": scale["scale_code"], "items": sorted(unknown)},
            )
    interpreter = RuleInterpreter()
    for item in items:
        if item.get("item_type") not in {
            "single_choice",
            "integer",
            "decimal",
            "boolean",
        }:
            raise DomainError(
                "METHODOLOGY_SCHEMA_INVALID", "Item type is outside the MVP whitelist"
            )
        if item.get("item_transform_expr"):
            interpreter.validate(item["item_transform_expr"])
        if item.get("item_type") == "single_choice" and not item.get("options"):
            raise DomainError(
                "METHODOLOGY_SCHEMA_INVALID", "single_choice item requires options"
            )
    for scale in scales:
        for field in ("unit_code", "theoretical_min", "theoretical_max", "aggregation"):
            if field not in scale:
                raise DomainError(
                    "METHODOLOGY_SCHEMA_INVALID", f"Scale requires {field}"
                )
        decimal_value(scale["theoretical_min"])
        decimal_value(scale["theoretical_max"])
        if scale.get("transform_expr"):
            interpreter.validate(scale["transform_expr"])
        if scale.get("norm"):
            _validate_norm(scale["norm"])
    norm = snapshot.get("norm")
    if norm:
        _validate_norm(norm)
    for rule in snapshot.get("interpretations", []):
        interpreter.validate(rule["when"])
        if default_locale not in rule.get("text_i18n", {}):
            raise DomainError(
                "METHODOLOGY_SCHEMA_INVALID", "Interpretation lacks default locale"
            )


def _validate_norm(norm: dict) -> None:
    bands = norm.get("bands", [])
    for band in bands:
        if band.get("lower_bound") is not None:
            decimal_value(band["lower_bound"])
        if band.get("upper_bound") is not None:
            decimal_value(band["upper_bound"])
    ordered = sorted(
        bands,
        key=lambda b: (
            decimal_value(b["lower_bound"])
            if b.get("lower_bound") is not None
            else decimal_value("-999999999999999999")
        ),
    )
    for previous, current in zip(ordered, ordered[1:]):
        if previous.get("upper_bound") is None:
            raise DomainError(
                "NORM_OVERLAP", "Unbounded norm band cannot precede another band"
            )
        upper = decimal_value(previous["upper_bound"])
        lower = (
            decimal_value(current["lower_bound"])
            if current.get("lower_bound") is not None
            else upper
        )
        if (
            upper > lower
            or upper == lower
            and previous.get("upper_inclusive")
            and current.get("lower_inclusive")
        ):
            raise DomainError("NORM_OVERLAP", "Norm bands overlap")


def create_version(
    db: Session,
    methodology: Methodology,
    payload: MethodologyVersionCreate,
    actor_id: str,
) -> MethodologyVersion:
    validate_snapshot(payload.snapshot, payload.default_locale)
    if db.scalar(
        select(MethodologyVersion).where(
            MethodologyVersion.methodology_id == methodology.id,
            MethodologyVersion.version_code == payload.version_code,
        )
    ):
        raise DomainError(
            "METHODOLOGY_VERSION_EXISTS", "Version code already exists", 409
        )
    snapshot = payload.snapshot
    snapshot.setdefault("methodology_code", methodology.methodology_code)
    snapshot.setdefault("version_code", payload.version_code)
    digest = canonical_hash(snapshot)
    version = MethodologyVersion(
        methodology_id=methodology.id,
        version_code=payload.version_code,
        default_locale=payload.default_locale,
        supported_locales=payload.supported_locales,
        target_population=payload.target_population,
        estimated_minutes=payload.estimated_minutes,
        disclaimer_i18n=payload.disclaimer_i18n,
        snapshot=snapshot,
        template_id=f"tmpl_{digest[7:19]}",
        created_by=actor_id,
    )
    db.add(version)
    db.flush()
    _materialize_snapshot(db, version, snapshot)
    audit(
        db,
        actor_id=actor_id,
        action="methodology_version.create",
        object_type="methodology_version",
        object_id=version.id,
    )
    return version


def _materialize_snapshot(
    db: Session, version: MethodologyVersion, snapshot: dict
) -> None:
    items: dict[str, Item] = {}
    for position, data in enumerate(snapshot["items"], 1):
        item = Item(
            methodology_version_id=version.id,
            item_code=data["item_code"],
            item_type=data["item_type"],
            prompt_i18n=data.get(
                "prompt_i18n", {version.default_locale: data["item_code"]}
            ),
            required=data.get("required", True),
            value_constraints=data.get("value_constraints", {}),
            missing_policy=data.get(
                "missing_policy", {"mode": "allow", "counts_as_missing": True}
            ),
            score_mapping=data.get("score_mapping", {"mode": "identity"}),
            reverse_scoring=data.get("reverse_scoring", {"mode": "none"}),
            item_transform_expr=data.get("item_transform_expr"),
            sort_order=data.get("sort_order", position),
        )
        db.add(item)
        db.flush()
        items[item.item_code] = item
        for option_position, option in enumerate(data.get("options", [])):
            db.add(
                ResponseOption(
                    item_id=item.id,
                    option_code=option["option_code"],
                    label_i18n=option.get(
                        "label_i18n", {version.default_locale: option["option_code"]}
                    ),
                    ordinal_position=option.get("ordinal_position", option_position),
                    score_value=str(option["score_value"]),
                )
            )
    for position, data in enumerate(snapshot["scales"], 1):
        scale = Scale(
            methodology_version_id=version.id,
            scale_code=data["scale_code"],
            scale_kind=data["scale_kind"],
            label_i18n=data.get(
                "label_i18n", {version.default_locale: data["scale_code"]}
            ),
            unit_code=data["unit_code"],
            theoretical_min=str(data["theoretical_min"]),
            theoretical_max=str(data["theoretical_max"]),
            display_decimals=data.get("display_decimals", 2),
            aggregation=data["aggregation"],
            transform_expr=data.get("transform_expr"),
            validity_rules=data.get("validity_rules", []),
            sort_order=data.get("sort_order", position),
        )
        db.add(scale)
        db.flush()
        for link_position, code in enumerate(data.get("item_codes") or items.keys(), 1):
            db.add(
                ScaleItemLink(
                    scale_id=scale.id,
                    item_id=items[code].id,
                    weight=str(data.get("weights", {}).get(code, "1")),
                    sort_order=link_position,
                )
            )
        norm_data = data.get("norm") or snapshot.get("norm")
        if norm_data:
            norm = NormSet(
                methodology_version_id=version.id,
                scale_id=scale.id,
                norm_code=norm_data["norm_code"],
                label_i18n=norm_data.get(
                    "label_i18n", {version.default_locale: norm_data["norm_code"]}
                ),
                norm_kind=norm_data.get("norm_kind", "threshold_bands"),
                population_descriptor=norm_data.get("population_descriptor", {}),
                selection_constraints=norm_data.get("selection_constraints", {}),
                source_reference=norm_data["source_reference"],
                is_default=True,
            )
            db.add(norm)
            db.flush()
            for band_position, band in enumerate(norm_data.get("bands", []), 1):
                db.add(
                    NormBand(
                        norm_set_id=norm.id,
                        band_code=band["band_code"],
                        lower_bound=band.get("lower_bound"),
                        lower_inclusive=band.get("lower_inclusive", False),
                        upper_bound=band.get("upper_bound"),
                        upper_inclusive=band.get("upper_inclusive", False),
                        normalized_value=band.get("normalized_value"),
                        label_i18n=band.get(
                            "label_i18n", {version.default_locale: band["band_code"]}
                        ),
                        sort_order=band_position,
                    )
                )
        for rule in snapshot.get("interpretations", []):
            if rule.get("scale_code", scale.scale_code) == scale.scale_code:
                db.add(
                    InterpretationRule(
                        methodology_version_id=version.id,
                        scale_id=scale.id,
                        rule_code=rule["rule_code"],
                        priority=rule.get("priority", 100),
                        when_expr=rule["when"],
                        interpretation_code=rule["interpretation_code"],
                        title_i18n=rule.get("title_i18n", {}),
                        text_i18n=rule["text_i18n"],
                        disclaimer_i18n=rule.get("disclaimer_i18n", {}),
                    )
                )


def create_licence(
    db: Session, version: MethodologyVersion, payload: LicenceCreate, actor_id: str
) -> LicenceRevision:
    latest = (
        db.scalar(
            select(func.max(LicenceRevision.licence_revision)).where(
                LicenceRevision.methodology_version_id == version.id
            )
        )
        or 0
    )
    licence = LicenceRevision(
        methodology_version_id=version.id,
        licence_revision=latest + 1,
        verified_by=actor_id,
        verified_at=datetime.now(UTC),
        **payload.model_dump(),
    )
    db.add(licence)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        action="licence.revise",
        object_type="licence",
        object_id=licence.id,
        safe_metadata={"status": licence.status, "revision": licence.licence_revision},
    )
    return licence


def publish_version(
    db: Session, version: MethodologyVersion, actor_id: str, reason: str
) -> MethodologyVersion:
    if version.lifecycle_status == "published":
        return version
    if version.lifecycle_status not in {"draft", "in_review"}:
        raise DomainError(
            "VERSION_STATE_INVALID",
            "Only draft or in-review version can be published",
            409,
        )
    validate_snapshot(version.snapshot, version.default_locale)
    licence = latest_licence(db, version.id)
    if not licence:
        raise DomainError(
            "LICENCE_METADATA_REQUIRED", "A licence revision is required before publish"
        )
    version.content_hash = canonical_hash(version.snapshot)
    version.lifecycle_status = "published"
    version.published_at = datetime.now(UTC)
    version.published_by = actor_id
    audit(
        db,
        actor_id=actor_id,
        action="methodology_version.publish",
        object_type="methodology_version",
        object_id=version.id,
        safe_metadata={"reason": reason[:200]},
    )
    return version


def latest_licence(db: Session, version_id: str) -> LicenceRevision | None:
    return db.scalar(
        select(LicenceRevision)
        .where(LicenceRevision.methodology_version_id == version_id)
        .order_by(LicenceRevision.licence_revision.desc())
    )


def check_licence(
    licence: LicenceRevision | None,
    *,
    org_type: str,
    region: str,
    use_type: str,
    today: date | None = None,
) -> None:
    today = today or datetime.now(UTC).date()
    if (
        not licence
        or licence.status != "verified"
        or licence.valid_from > today
        or licence.valid_until is not None
        and licence.valid_until < today
        or use_type not in licence.allowed_use_types
        or org_type not in licence.allowed_org_types
        or region not in licence.allowed_regions
        and "GLOBAL" not in licence.allowed_regions
    ):
        raise DomainError(
            "LICENCE_NOT_VALID",
            "Methodology licence is not valid for this context",
            409,
        )
