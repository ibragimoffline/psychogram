from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.errors import DomainError
from src.models.domain import (
    CalculationRun,
    ExplainabilityTrace,
    LicenceRevision,
    MethodologyVersion,
    Organization,
    Research,
    ResearchMethodologyPin,
    Response,
    ResponseRevision,
    Result,
    Scale,
    ScaleResult,
    TraceStep,
)
from src.services.audit import audit
from src.services.domain import require_valid_consent
from src.services.registry import canonical_hash, check_licence, latest_licence
from src.services.scoring_engine import DISCLAIMER, score_snapshot

ENGINE_VERSION = "psychogram-scoring/1"
INTERPRETER_VERSION = "json-ast/1"
ROUNDING_VERSION = "decimal-half-up/1"


def calculate(
    db: Session,
    *,
    tenant: Organization,
    research: Research,
    revision_id: str,
    idempotency_key: str,
    actor_id: str,
) -> Result:
    if research.tenant_id != tenant.id:
        raise DomainError(
            "TENANT_ACCESS_DENIED", "Research is outside the active organization", 404
        )
    revision = db.scalar(
        select(ResponseRevision).where(
            ResponseRevision.id == revision_id,
            ResponseRevision.tenant_id == tenant.id,
            ResponseRevision.research_id == research.id,
        )
    )
    if not revision:
        raise DomainError("REVISION_NOT_FOUND", "Response revision was not found", 404)
    response = db.scalar(
        select(Response).where(
            Response.id == revision.response_id,
            Response.tenant_id == tenant.id,
            Response.research_id == research.id,
        )
    )
    if not response:
        raise DomainError("RESPONSE_NOT_FOUND", "Response was not found", 404)
    version = db.get(MethodologyVersion, research.methodology_version_id)
    pin = db.scalar(
        select(ResearchMethodologyPin).where(
            ResearchMethodologyPin.tenant_id == tenant.id,
            ResearchMethodologyPin.research_id == research.id,
        )
    )
    if not version or not pin or pin.methodology_content_hash != version.content_hash:
        raise DomainError(
            "METHODOLOGY_HASH_MISMATCH",
            "Pinned methodology hash does not match the published snapshot",
            409,
        )
    computation_key = canonical_hash(
        {
            "tenant_id": tenant.id,
            "research_id": research.id,
            "response_revision_id": revision.id,
            "answer_payload_hash": revision.answer_payload_hash,
            "methodology_content_hash": version.content_hash,
            "norm_selection": pin.norm_selection,
            "engine_version": ENGINE_VERSION,
            "interpreter_version": INTERPRETER_VERSION,
            "rounding_version": ROUNDING_VERSION,
        }
    )
    existing_idempotency = db.scalar(
        select(CalculationRun).where(
            CalculationRun.tenant_id == tenant.id,
            CalculationRun.idempotency_key == idempotency_key,
        )
    )
    if existing_idempotency:
        if existing_idempotency.computation_key != computation_key:
            raise DomainError(
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for another computation",
                409,
            )
        result = db.scalar(
            select(Result).where(Result.calculation_run_id == existing_idempotency.id)
        )
        if result:
            return result
        raise DomainError(
            "CALCULATION_IN_PROGRESS", "The calculation is already in progress", 409
        )
    existing_computation = db.scalar(
        select(CalculationRun).where(
            CalculationRun.tenant_id == tenant.id,
            CalculationRun.computation_key == computation_key,
        )
    )
    if existing_computation:
        result = db.scalar(
            select(Result).where(Result.calculation_run_id == existing_computation.id)
        )
        if result:
            return result
        raise DomainError(
            "CALCULATION_IN_PROGRESS", "The calculation is already in progress", 409
        )

    if research.status != "active":
        raise DomainError(
            "RESEARCH_NOT_ACTIVE", "Scoring requires active research", 409
        )
    if response.current_revision_id != revision.id or revision.status != "validated":
        raise DomainError(
            "RESPONSE_NOT_VALIDATED",
            "Scoring requires the validated current revision",
            409,
        )
    consent = require_valid_consent(db, response.participant_id)
    licence = latest_licence(db, version.id)
    check_licence(
        licence,
        org_type=tenant.org_type,
        region=tenant.region,
        use_type=research.use_type,
    )
    if version.lifecycle_status != "published":
        raise DomainError(
            "METHODOLOGY_NOT_PUBLISHED", "Only a published version can be scored", 409
        )
    assert licence is not None
    disclosure = _effective_disclosure(licence)
    run = CalculationRun(
        tenant_id=tenant.id,
        research_id=research.id,
        response_revision_id=revision.id,
        idempotency_key=idempotency_key,
        computation_key=computation_key,
        status="running",
        engine_version=ENGINE_VERSION,
        rule_interpreter_version=INTERPRETER_VERSION,
        methodology_version_id=version.id,
        methodology_content_hash=version.content_hash,
        licence_id=licence.id,
        licence_revision=licence.licence_revision,
        initiated_by=actor_id,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        tenant_id=tenant.id,
        research_id=research.id,
        action="calculation.start",
        object_type="calculation_run",
        object_id=run.id,
    )
    scored = score_snapshot(version.snapshot, revision.answers, disclosure)

    # Optimistic gate recheck immediately before immutable persistence.
    db.refresh(research)
    db.refresh(consent)
    current_licence = latest_licence(db, version.id)
    if research.status != "active":
        raise DomainError(
            "RESEARCH_CHANGED_DURING_RUN",
            "Research state changed during calculation",
            409,
        )
    if consent.status not in {"granted", "not_required_with_basis"}:
        raise DomainError(
            "CONSENT_CHANGED_DURING_RUN", "Consent changed during calculation", 409
        )
    if not current_licence or current_licence.id != licence.id:
        raise DomainError(
            "LICENCE_CHANGED_DURING_RUN", "Licence changed during calculation", 409
        )
    check_licence(
        current_licence,
        org_type=tenant.org_type,
        region=tenant.region,
        use_type=research.use_type,
    )

    trace_hash = canonical_hash(scored["trace"])
    result_payload = {
        "revision_hash": revision.answer_payload_hash,
        "methodology_hash": version.content_hash,
        "status": scored["status"],
        "scales": scored["scales"],
        "trace_hash": trace_hash,
        "engine_version": ENGINE_VERSION,
    }
    result = Result(
        calculation_run_id=run.id,
        tenant_id=tenant.id,
        research_id=research.id,
        participant_id=response.participant_id,
        response_id=response.id,
        response_revision_id=revision.id,
        methodology_version_id=version.id,
        methodology_content_hash=version.content_hash,
        status=scored["status"],
        disclaimer_i18n_snapshot=version.disclaimer_i18n or {"uz-Latn": DISCLAIMER},
        calculated_at=datetime.now(UTC),
        calculated_by=actor_id,
        result_hash=canonical_hash(result_payload),
    )
    db.add(result)
    db.flush()
    scale_rows = {
        scale.scale_code: scale
        for scale in db.scalars(
            select(Scale).where(Scale.methodology_version_id == version.id)
        ).all()
    }
    for output in scored["scales"]:
        scale = scale_rows.get(output["scale_code"])
        db.add(
            ScaleResult(
                result_id=result.id,
                scale_id=scale.id if scale else None,
                scale_code=output["scale_code"],
                validity_status=output["validity_status"],
                reason_codes=output["reason_codes"],
                answered_count=output["answered_count"],
                missing_count=output["missing_count"],
                aggregate_score_unrounded=output["aggregate_score_unrounded"],
                score_unrounded=output["score_unrounded"],
                score_display=output["score_display"],
                unit_code=output["unit_code"],
                norm_band_code=output["norm_band_code"],
                normalized_value=output["normalized_value"],
                interpretation_code=output["interpretation_code"],
                interpretation_snapshot_i18n=output["interpretation_snapshot_i18n"],
                disclosure_level_applied=output["disclosure_level_applied"],
            )
        )
    trace = ExplainabilityTrace(
        calculation_run_id=run.id,
        result_id=result.id,
        disclosure_level_applied=disclosure,
        methodology_content_hash=version.content_hash,
        response_revision_hash=revision.answer_payload_hash,
        trace_hash=trace_hash,
    )
    db.add(trace)
    db.flush()
    for step in scored["trace"]:
        db.add(
            TraceStep(
                trace_id=trace.id,
                sequence=step["sequence"],
                step_code=step["step_code"],
                status=step["status"],
                entity_ref=step["entity_ref"],
                rule_ref=step["rule_ref"],
                inputs=step["inputs"],
                outputs=step["outputs"],
                reason_code=step["reason_code"],
                message_key=step["message_key"],
                redactions=step["redactions"],
            )
        )
    response.status = "scored"
    run.status = "succeeded"
    run.finished_at = datetime.now(UTC)
    audit(
        db,
        actor_id=actor_id,
        tenant_id=tenant.id,
        research_id=research.id,
        action="calculation.succeed",
        object_type="result",
        object_id=result.id,
        safe_metadata={"result_hash": result.result_hash},
    )
    return result


def result_view(db: Session, result: Result) -> dict:
    scales = db.scalars(
        select(ScaleResult)
        .where(ScaleResult.result_id == result.id)
        .order_by(ScaleResult.scale_code)
    ).all()
    trace = db.scalar(
        select(ExplainabilityTrace).where(ExplainabilityTrace.result_id == result.id)
    )
    steps: Sequence[TraceStep] = ()
    if trace:
        steps = db.scalars(
            select(TraceStep)
            .where(TraceStep.trace_id == trace.id)
            .order_by(TraceStep.sequence)
        ).all()
    return {
        "id": result.id,
        "research_id": result.research_id,
        "participant_id": result.participant_id,
        "response_revision_id": result.response_revision_id,
        "status": result.status,
        "disclaimer_i18n": result.disclaimer_i18n_snapshot,
        "calculated_at": result.calculated_at,
        "result_hash": result.result_hash,
        "scales": [
            {
                "scale_code": row.scale_code,
                "validity_status": row.validity_status,
                "reason_codes": row.reason_codes,
                "answered_count": row.answered_count,
                "missing_count": row.missing_count,
                "aggregate_score_unrounded": row.aggregate_score_unrounded,
                "score_unrounded": row.score_unrounded,
                "score_display": row.score_display,
                "unit_code": row.unit_code,
                "norm_band_code": row.norm_band_code,
                "interpretation_code": row.interpretation_code,
                "interpretation_snapshot_i18n": row.interpretation_snapshot_i18n,
                "disclosure_level_applied": row.disclosure_level_applied,
            }
            for row in scales
        ],
        "trace": [
            {
                "sequence": row.sequence,
                "step_code": row.step_code,
                "status": row.status,
                "entity_ref": row.entity_ref,
                "rule_ref": row.rule_ref,
                "inputs": row.inputs,
                "outputs": row.outputs,
                "reason_code": row.reason_code,
                "redactions": row.redactions,
            }
            for row in steps
        ],
    }


def _effective_disclosure(licence: LicenceRevision) -> str:
    if licence.content_disclosure_level == "summary_only":
        return "summary_only"
    if (
        licence.content_disclosure_level == "derived_only"
        or not licence.allow_trace_item_values
    ):
        return "derived_only"
    return "full"
