from __future__ import annotations

import csv
import io
from typing import Any

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.domain import (
    Methodology,
    MethodologyVersion,
    Organization,
    Participant,
    Research,
    Response,
    ResponseRevision,
    Result,
    ScaleResult,
)
from src.services.domain import latest_consent
from src.services.orchestration import result_view
from src.services.registry import check_licence, latest_licence

DISCLAIMER = "Bu natija tibbiy tashxis emas."
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def build_json_export(
    db: Session, result: Result, disclosure_level: str
) -> dict[str, Any]:
    payload = result_view(db, result)
    payload["calculated_at"] = result.calculated_at.isoformat()
    payload["export_disclosure_level"] = disclosure_level
    payload["disclaimer"] = DISCLAIMER
    payload["trace"] = redact_trace(payload["trace"], disclosure_level)
    return payload


def build_csv_export(db: Session, result: Result, disclosure_level: str) -> str:
    payload = build_json_export(db, result, disclosure_level)
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(["field", "value"])
    writer.writerow(["result_id", csv_safe(payload["id"])])
    writer.writerow(["research_id", csv_safe(payload["research_id"])])
    writer.writerow(["participant_id", csv_safe(payload["participant_id"])])
    writer.writerow(["response_revision_id", csv_safe(payload["response_revision_id"])])
    writer.writerow(["calculated_at", csv_safe(payload["calculated_at"])])
    writer.writerow(["disclosure_level", csv_safe(disclosure_level)])
    writer.writerow(["disclaimer", csv_safe(DISCLAIMER)])
    writer.writerow([])
    writer.writerow(
        [
            "scale_code",
            "validity_status",
            "score_display",
            "unit_code",
            "norm_band_code",
            "interpretation_code",
            "interpretation_uz_latn",
            "disclaimer",
        ]
    )
    for scale in payload["scales"]:
        interpretation = (scale.get("interpretation_snapshot_i18n") or {}).get(
            "uz-Latn", ""
        )
        writer.writerow(
            [
                csv_safe(scale.get("scale_code")),
                csv_safe(scale.get("validity_status")),
                csv_safe(scale.get("score_display")),
                csv_safe(scale.get("unit_code")),
                csv_safe(scale.get("norm_band_code")),
                csv_safe(scale.get("interpretation_code")),
                csv_safe(interpretation),
                csv_safe(DISCLAIMER),
            ]
        )
    return output.getvalue()


@dataclass
class ResearchExport:
    csv_text: str
    rows: int
    not_calculated: int
    excluded_consent: int


def build_research_csv(
    db: Session, tenant: Organization, research: Research
) -> ResearchExport:
    """One row per respondent with the result of their current answers.

    The whole file is refused when the licence does not allow use; rows whose
    participant no longer has valid consent are left out and counted.
    """
    version = db.get(MethodologyVersion, research.methodology_version_id)
    methodology = db.get(Methodology, version.methodology_id) if version else None
    assert version is not None and methodology is not None
    check_licence(
        latest_licence(db, version.id),
        org_type=tenant.org_type,
        region=tenant.region,
        use_type=research.use_type,
    )
    snapshot = version.snapshot
    interpreted = {
        rule.get("scale_code") for rule in snapshot.get("interpretations", [])
    }
    columns: list[tuple[str, str, str]] = []
    for scale in snapshot["scales"]:
        code = scale["scale_code"]
        columns += [(f"{code}_score", code, "score_display")]
        columns += [(f"{code}_validity_status", code, "validity_status")]
        if scale.get("norm") or snapshot.get("norm"):
            columns += [(f"{code}_norm_band", code, "norm_band_code")]
        if code in interpreted or None in interpreted:
            columns += [(f"{code}_interpretation_code", code, "interpretation_code")]

    output = io.StringIO(newline="")
    output.write("\ufeff")  # lets Excel detect UTF-8
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(
        [
            "participant_code",
            "methodology_code",
            "version_code",
            "response_revision",
            "result_id",
            "calculated_at",
        ]
        + [name for name, _, _ in columns]
    )
    rows = not_calculated = excluded_consent = 0
    responses = db.execute(
        select(Response, Participant)
        .join(Participant, Participant.id == Response.participant_id)
        .where(
            Response.tenant_id == research.tenant_id,
            Response.research_id == research.id,
        )
        .order_by(Participant.external_code, Response.attempt_key)
    ).all()
    for response, participant in responses:
        consent = latest_consent(db, participant.id)
        if not consent or consent.status not in {"granted", "not_required_with_basis"}:
            excluded_consent += 1
            continue
        result = db.scalar(
            select(Result)
            .where(
                Result.tenant_id == research.tenant_id,
                Result.response_revision_id == response.current_revision_id,
            )
            .order_by(Result.calculated_at.desc())
        )
        if not result:
            not_calculated += 1
            continue
        revision = db.get(ResponseRevision, result.response_revision_id)
        scales = {
            row.scale_code: row
            for row in db.scalars(
                select(ScaleResult).where(ScaleResult.result_id == result.id)
            ).all()
        }
        values: list[str] = []
        for _, scale_code, field in columns:
            value = getattr(scales[scale_code], field) if scale_code in scales else None
            # Scores are canonical decimals from the engine and stay numeric for analysis.
            values.append(value or "" if field == "score_display" else csv_safe(value))
        writer.writerow(
            [
                csv_safe(participant.external_code),
                csv_safe(methodology.methodology_code),
                csv_safe(version.version_code),
                revision.revision_number if revision else "",
                result.id,
                result.calculated_at.isoformat(),
            ]
            + values
        )
        rows += 1
    return ResearchExport(output.getvalue(), rows, not_calculated, excluded_consent)


def redact_trace(trace: list[dict[str, Any]], disclosure_level: str) -> list[dict]:
    if disclosure_level == "summary_only":
        return [
            step
            for step in trace
            if not step.get("entity_ref") or step["entity_ref"].get("kind") != "item"
        ]
    if disclosure_level == "derived_only":
        redacted = []
        for step in trace:
            copy = dict(step)
            copy["inputs"] = []
            copy["redactions"] = sorted(
                set(copy.get("redactions", [])) | {"raw_answer", "prompt", "label"}
            )
            redacted.append(copy)
        return redacted
    return trace
