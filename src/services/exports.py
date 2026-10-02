from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from src.models.domain import Result
from src.services.orchestration import result_view

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
