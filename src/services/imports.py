from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.errors import DomainError
from src.models.domain import (
    ImportIssue,
    ImportJob,
    ImportRow,
    Methodology,
    MethodologyVersion,
    Participant,
    Research,
    Response,
)
from src.schemas.api import ResponseCreate
from src.services.audit import audit
from src.services.domain import create_response, require_valid_consent
from src.services.registry import canonical_hash
from src.services.rule_engine import decimal_value
from src.services.scoring_engine import validate_answers

PII_HEADERS = {
    "name",
    "full_name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "telephone",
    "address",
    "passport",
    "national_id",
    "birth_date",
    "date_of_birth",
}
RESERVED = {
    "_methodology_code",
    "_version_code",
    "_template_id",
    "participant_external_code",
    "attempt_key",
    "collected_at",
}
INTEGER_RE = re.compile(r"^(?:0|-[1-9]\d*|[1-9]\d*)$")


def preview_csv(
    db: Session,
    *,
    research: Research,
    csv_text: str,
    actor_id: str,
    max_bytes: int,
    max_rows: int,
) -> tuple[ImportJob, list[dict]]:
    if research.status != "active":
        raise DomainError("RESEARCH_NOT_ACTIVE", "Import requires active research", 409)
    encoded = csv_text.encode("utf-8")
    if len(encoded) > max_bytes:
        raise DomainError("FILE_TOO_LARGE", "CSV exceeds configured byte limit", 413)
    try:
        rows = list(csv.reader(io.StringIO(csv_text, newline=""), strict=True))
    except csv.Error as exc:
        raise DomainError("CSV_MALFORMED", "CSV could not be parsed") from exc
    if not rows:
        raise DomainError("CSV_MALFORMED", "CSV has no header")
    headers = [header.strip().lstrip("\ufeff") for header in rows[0]]
    if len(headers) != len(set(headers)):
        raise DomainError("DUPLICATE_HEADER", "CSV contains duplicate headers")
    if len(rows) - 1 > max_rows:
        raise DomainError("FILE_TOO_LARGE", "CSV exceeds configured row limit", 413)
    version = db.get(MethodologyVersion, research.methodology_version_id)
    methodology = db.get(Methodology, version.methodology_id) if version else None
    if not version or not methodology:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND",
            "Pinned methodology version is missing",
            409,
        )
    pii = next((header for header in headers if header.lower() in PII_HEADERS), None)
    if pii:
        raise DomainError("PII_COLUMN_FORBIDDEN", f"PII column '{pii}' is forbidden")
    item_headers = {f"item.{item['item_code']}" for item in version.snapshot["items"]}
    unknown = [
        header
        for header in headers
        if header not in RESERVED and header not in item_headers
    ]
    if unknown:
        raise DomainError("UNKNOWN_COLUMN", f"Unknown CSV column '{unknown[0]}'")
    required = {
        "_methodology_code",
        "_version_code",
        "_template_id",
        "participant_external_code",
    }
    required |= {
        f"item.{item['item_code']}"
        for item in version.snapshot["items"]
        if item.get("required", True)
    }
    missing = required - set(headers)
    if missing:
        raise DomainError(
            "REQUIRED_COLUMN_MISSING",
            f"Required column '{sorted(missing)[0]}' is missing",
        )
    dictionaries = [
        dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in rows[1:]
    ]
    identities = [
        (
            row.get("participant_external_code", "").strip(),
            row.get("attempt_key", "").strip() or "initial",
        )
        for row in dictionaries
    ]
    counts = Counter(identities)
    errors: list[dict] = []
    staged: list[dict] = []
    duplicate_rows = 0
    for row_number, row in enumerate(dictionaries, 2):
        code = row.get("participant_external_code", "").strip()
        attempt = row.get("attempt_key", "").strip() or "initial"
        row_errors: list[dict] = []
        if (
            row.get("_methodology_code", "").strip() != methodology.methodology_code
            or row.get("_version_code", "").strip() != version.version_code
            or row.get("_template_id", "").strip() != version.template_id
        ):
            row_errors.append(_issue(row_number, None, "TEMPLATE_MISMATCH"))
        if counts[(code, attempt)] > 1:
            duplicate_rows += 1
            row_errors.append(
                _issue(row_number, "participant_external_code", "ROW_DUPLICATE")
            )
        participant = db.scalar(
            select(Participant).where(
                Participant.tenant_id == research.tenant_id,
                Participant.research_id == research.id,
                Participant.external_code == code,
            )
        )
        if not participant:
            row_errors.append(
                _issue(row_number, "participant_external_code", "PARTICIPANT_NOT_FOUND")
            )
        else:
            try:
                require_valid_consent(db, participant.id)
            except DomainError:
                row_errors.append(
                    _issue(row_number, "participant_external_code", "CONSENT_NOT_VALID")
                )
        answers: dict = {}
        for item in version.snapshot["items"]:
            header = f"item.{item['item_code']}"
            cell = row.get(header, "").strip()
            if cell == "":
                continue
            try:
                answers[item["item_code"]] = _parse_cell(item, cell)
            except DomainError as exc:
                row_errors.append(
                    _issue(row_number, header, exc.code, item["item_code"])
                )
        for validation in validate_answers(version.snapshot, answers):
            row_errors.append(
                _issue(
                    row_number,
                    (
                        f"item.{validation.get('item_code')}"
                        if validation.get("item_code")
                        else None
                    ),
                    validation["error_code"],
                    validation.get("item_code"),
                )
            )
        if db.scalar(
            select(Response).where(
                Response.tenant_id == research.tenant_id,
                Response.research_id == research.id,
                (
                    Response.participant_id == participant.id
                    if participant
                    else Response.participant_id == ""
                ),
                Response.attempt_key == attempt,
            )
        ):
            row_errors.append(_issue(row_number, "attempt_key", "ROW_DUPLICATE"))
        if row_errors:
            errors.extend(row_errors)
        elif participant:
            staged.append(
                {
                    "row_number": row_number,
                    "participant_id": participant.id,
                    "attempt_key": attempt,
                    "answers": answers,
                }
            )
    summary = {
        "total_rows": len(dictionaries),
        "valid_rows": len(staged),
        "invalid_rows": len({error["row_number"] for error in errors}) - duplicate_rows,
        "duplicate_rows": duplicate_rows,
    }
    file_hash = "sha256:" + hashlib.sha256(encoded).hexdigest()
    preview_hash = canonical_hash(
        {
            "file_hash": file_hash,
            "research_id": research.id,
            "staged": staged,
            "errors": errors,
        }
    )
    job = ImportJob(
        tenant_id=research.tenant_id,
        research_id=research.id,
        status="preview_ready",
        file_hash=file_hash,
        preview_hash=preview_hash,
        summary=summary,
        staged_rows=staged,
        created_by=actor_id,
    )
    db.add(job)
    db.flush()
    for error in errors:
        db.add(
            ImportIssue(
                import_job_id=job.id,
                row_number=error["row_number"],
                column_name=error["column_name"],
                item_code=error["item_code"],
                error_code=error["error_code"],
                safe_params={},
            )
        )
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="import.preview",
        object_type="import_job",
        object_id=job.id,
        safe_metadata=summary,
    )
    return job, errors


def confirm_import(
    db: Session, *, job: ImportJob, research: Research, preview_hash: str, actor_id: str
) -> ImportJob:
    if job.tenant_id != research.tenant_id or job.research_id != research.id:
        raise DomainError(
            "TENANT_ACCESS_DENIED", "Import job is outside the active research", 404
        )
    if job.status != "preview_ready":
        raise DomainError(
            "IMPORT_STATE_INVALID", "Only a preview-ready import can be confirmed", 409
        )
    if job.preview_hash != preview_hash:
        raise DomainError("IMPORT_PREVIEW_CHANGED", "Preview hash does not match", 409)
    if research.status != "active":
        raise DomainError("RESEARCH_NOT_ACTIVE", "Import requires active research", 409)
    job.status = "committing"
    accepted = 0
    rejected = 0
    for staged in job.staged_rows:
        try:
            response, _revision = create_response(
                db,
                research,
                ResponseCreate(
                    participant_id=staged["participant_id"],
                    attempt_key=staged["attempt_key"],
                    answers=staged["answers"],
                    finalize=True,
                ),
                actor_id,
            )
            db.add(
                ImportRow(
                    import_job_id=job.id,
                    row_number=staged["row_number"],
                    status="accepted",
                    participant_id=staged["participant_id"],
                    response_id=response.id,
                )
            )
            accepted += 1
        except DomainError as exc:
            db.add(
                ImportRow(
                    import_job_id=job.id,
                    row_number=staged["row_number"],
                    status="rejected",
                    participant_id=staged["participant_id"],
                )
            )
            db.add(
                ImportIssue(
                    import_job_id=job.id,
                    row_number=staged["row_number"],
                    error_code=exc.code,
                    safe_params={},
                )
            )
            rejected += 1
    job.status = "completed"
    job.confirmed_at = datetime.now(UTC)
    job.confirmed_by = actor_id
    job.summary = {
        **job.summary,
        "accepted_rows": accepted,
        "commit_rejected_rows": rejected,
    }
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="import.confirm",
        object_type="import_job",
        object_id=job.id,
        safe_metadata={"accepted_rows": accepted, "rejected_rows": rejected},
    )
    return job


def _parse_cell(item: dict, cell: str):
    kind = item["item_type"]
    if kind == "integer":
        if not INTEGER_RE.fullmatch(cell):
            raise DomainError("TYPE_INVALID", "Integer cell is invalid")
        return int(cell)
    if kind == "decimal":
        decimal_value(cell)
        return cell
    if kind == "boolean":
        if cell not in {"true", "false"}:
            raise DomainError(
                "BOOLEAN_LITERAL_INVALID", "Boolean cell must be true or false"
            )
        return cell == "true"
    if kind == "single_choice":
        options = {option["option_code"] for option in item.get("options", [])}
        if cell not in options:
            raise DomainError("OPTION_NOT_ALLOWED", "Option code is not allowed")
        return cell
    raise DomainError("TYPE_INVALID", "Item type is unsupported")


def _issue(
    row: int, column: str | None, code: str, item_code: str | None = None
) -> dict:
    return {
        "row_number": row,
        "column_name": column,
        "item_code": item_code,
        "error_code": code,
        "severity": "error",
        "message_key": f"import.{code.lower()}",
        "safe_params": {},
        "rejected_value_preview": "***",
        "suggested_action": "CSV qiymatini tuzating",
    }
