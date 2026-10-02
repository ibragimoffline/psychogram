from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.dependencies import (
    TenantContext,
    current_user,
    get_db,
    get_runtime_settings,
    pii_access,
    roles,
    tenant_context,
)
from src.core.config import Settings
from src.core.errors import DomainError
from src.models.domain import (
    ConsentRecord,
    LicenceRevision,
    Membership,
    Methodology,
    MethodologyVersion,
    Organization,
    Participant,
    ParticipantPII,
    Research,
    Response as ResponseModel,
    ResponseRevision,
    Result,
    RetentionPolicy,
    ScaleResult,
    User,
)
from src.schemas.api import ScaleResultView, ValidationIssueView
from src.schemas.read import (
    ConsentHistoryItem,
    ConsentHistoryView,
    LicenceDetailView,
    MethodologyDetailView,
    MethodologyVersionDetailView,
    PIIView,
    PIIWrite,
    ParticipantDetailView,
    ParticipantListItem,
    ParticipantPage,
    ResponseDetailView,
    ResponseListItem,
    ResponsePage,
    ResultPage,
    ResultSummaryView,
    RetentionPolicyView,
    RevisionDetailView,
    RevisionHistoryView,
)
from src.services.audit import audit
from src.services.domain import validation_issues
from src.services.exports import build_csv_export, build_json_export
from src.services.orchestration import _effective_disclosure, require_result_policy
from src.services.pii import delete_pii, upsert_pii, view_pii
from src.services.registry import check_licence, latest_licence

router = APIRouter(prefix="/api/v1")


@router.get(
    "/retention-policies",
    response_model=list[RetentionPolicyView],
    tags=["research"],
)
def list_retention_policies(
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = True,
):
    query = select(RetentionPolicy).where(
        RetentionPolicy.tenant_id == context.organization.id
    )
    if active_only:
        query = query.where(RetentionPolicy.active.is_(True))
    return db.scalars(
        query.order_by(RetentionPolicy.code.asc(), RetentionPolicy.id.asc())
    ).all()


@router.get(
    "/methodologies/{methodology_id}",
    response_model=MethodologyDetailView,
    tags=["methodologies"],
)
def methodology_detail(
    methodology_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
):
    methodology = db.get(Methodology, methodology_id)
    if not methodology:
        raise DomainError("METHODOLOGY_NOT_FOUND", "Methodology was not found", 404)
    tenant = _catalog_tenant(db, user, organization_id)
    versions = _visible_versions(db, methodology.id, user, tenant)
    if not user.is_platform_admin and not versions:
        raise DomainError("METHODOLOGY_NOT_FOUND", "Methodology was not found", 404)
    return MethodologyDetailView(
        id=methodology.id,
        methodology_code=methodology.methodology_code,
        canonical_name=methodology.canonical_name,
        purpose_summary=methodology.purpose_summary,
        owner_name=methodology.owner_name,
        source_reference=(
            methodology.source_reference if user.is_platform_admin else None
        ),
        catalog_status=methodology.catalog_status,
        versions=versions,
    )


@router.get(
    "/methodologies/{methodology_id}/versions",
    response_model=list[MethodologyVersionDetailView],
    tags=["methodologies"],
)
def methodology_versions(
    methodology_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
):
    if not db.get(Methodology, methodology_id):
        raise DomainError("METHODOLOGY_NOT_FOUND", "Methodology was not found", 404)
    return _visible_versions(
        db, methodology_id, user, _catalog_tenant(db, user, organization_id)
    )


@router.get(
    "/methodology-versions/eligible",
    response_model=list[MethodologyVersionDetailView],
    tags=["methodologies"],
)
def eligible_versions(
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    use_type: str = Query("research", pattern="^(research|education|clinical)$"),
):
    versions = db.scalars(
        select(MethodologyVersion)
        .where(MethodologyVersion.lifecycle_status == "published")
        .order_by(
            MethodologyVersion.methodology_id.asc(),
            MethodologyVersion.version_code.asc(),
            MethodologyVersion.id.asc(),
        )
    ).all()
    visible: list[MethodologyVersionDetailView] = []
    for version in versions:
        licence = latest_licence(db, version.id)
        if _is_eligible(licence, context.organization, use_type):
            visible.append(_version_detail(version, licence, False, True))
    return visible


@router.get(
    "/methodology-versions/{version_id}",
    response_model=MethodologyVersionDetailView,
    tags=["methodologies"],
)
def methodology_version_detail(
    version_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
    use_type: Literal["research", "education", "clinical"] = "research",
    research_id: str | None = None,
):
    version = db.get(MethodologyVersion, version_id)
    if not version:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    tenant = _catalog_tenant(db, user, organization_id)
    licence = latest_licence(db, version.id)
    if research_id is not None:
        if tenant is None:
            raise DomainError(
                "ORGANIZATION_CONTEXT_REQUIRED",
                "X-Organization-ID is required for pinned research access",
                400,
            )
        research = db.scalar(
            select(Research).where(
                Research.id == research_id,
                Research.tenant_id == tenant.id,
            )
        )
        if not research or research.methodology_version_id != version.id:
            raise DomainError(
                "RESEARCH_METHODOLOGY_MISMATCH",
                "Research is not pinned to this methodology version",
                404,
            )
        if research.use_type not in {"research", "education", "clinical"}:
            raise DomainError(
                "RESEARCH_USE_TYPE_INVALID",
                "Pinned research has an invalid use type",
                409,
            )
        use_type = cast(Literal["research", "education", "clinical"], research.use_type)
    eligible = bool(tenant and _is_eligible(licence, tenant, use_type))
    if not user.is_platform_admin and (
        version.lifecycle_status != "published" or not eligible
    ):
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    return _version_detail(version, licence, user.is_platform_admin, eligible)


@router.get(
    "/methodology-versions/{version_id}/licences",
    response_model=list[LicenceDetailView],
    tags=["methodologies"],
)
def licence_history(
    version_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
):
    version = db.get(MethodologyVersion, version_id)
    if not version:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    tenant = _catalog_tenant(db, user, organization_id)
    licences = db.scalars(
        select(LicenceRevision)
        .where(LicenceRevision.methodology_version_id == version.id)
        .order_by(LicenceRevision.licence_revision.desc())
    ).all()
    current = licences[0] if licences else None
    eligible = bool(tenant and _is_eligible(current, tenant, "research"))
    if not user.is_platform_admin and (
        version.lifecycle_status != "published" or not eligible
    ):
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    return [
        _licence_detail(
            licence,
            private=user.is_platform_admin,
            current=licence.id == current.id if current else False,
            eligible=eligible and licence.id == current.id if current else False,
        )
        for licence in licences
    ]


@router.get(
    "/methodology-versions/{version_id}/licences/current",
    response_model=LicenceDetailView,
    tags=["methodologies"],
)
def current_licence(
    version_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
):
    history = licence_history(version_id, user, db, organization_id)
    if not history:
        raise DomainError("LICENCE_NOT_FOUND", "Licence was not found", 404)
    return history[0]


@router.get(
    "/researches/{research_id}/participants",
    response_model=ParticipantPage,
    tags=["participants"],
)
def participants(
    research_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    query: str | None = Query(None, max_length=120),
):
    research = _research(db, context, research_id)
    statement = select(Participant).where(
        Participant.tenant_id == research.tenant_id,
        Participant.research_id == research.id,
    )
    if query:
        statement = statement.where(Participant.external_code.contains(query))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(Participant.external_code.asc(), Participant.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ParticipantPage(
        items=[_participant_item(db, participant) for participant in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/researches/{research_id}/participants/{participant_id}",
    response_model=ParticipantDetailView,
    tags=["participants"],
)
def participant_detail(
    research_id: str,
    participant_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    participant = _participant(db, _research(db, context, research_id), participant_id)
    item = _participant_item(db, participant)
    return ParticipantDetailView(**item.model_dump(), created_by=participant.created_by)


@router.get(
    "/researches/{research_id}/participants/{participant_id}/consents",
    response_model=ConsentHistoryView,
    tags=["participants"],
)
def consent_history(
    research_id: str,
    participant_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    participant = _participant(db, _research(db, context, research_id), participant_id)
    records = db.scalars(
        select(ConsentRecord)
        .where(
            ConsentRecord.tenant_id == participant.tenant_id,
            ConsentRecord.research_id == participant.research_id,
            ConsentRecord.participant_id == participant.id,
        )
        .order_by(ConsentRecord.record_version.desc(), ConsentRecord.id.desc())
    ).all()
    history = [ConsentHistoryItem.model_validate(record) for record in records]
    return ConsentHistoryView(current=history[0] if history else None, history=history)


@router.get(
    "/researches/{research_id}/responses",
    response_model=ResponsePage,
    tags=["responses"],
)
def responses(
    research_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
    participant_id: str | None = None,
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    research = _research(db, context, research_id)
    statement = select(ResponseModel).where(
        ResponseModel.tenant_id == research.tenant_id,
        ResponseModel.research_id == research.id,
    )
    if participant_id:
        statement = statement.where(ResponseModel.participant_id == participant_id)
    if status:
        statement = statement.where(ResponseModel.status == status)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(ResponseModel.created_at.desc(), ResponseModel.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ResponsePage(
        items=[_response_item(db, row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/responses/{response_id}",
    response_model=ResponseDetailView,
    tags=["responses"],
)
def response_detail(
    response_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    response = _response(db, context, response_id)
    item = _response_item(db, response)
    revision = db.get(ResponseRevision, response.current_revision_id)
    raw_allowed = context.membership.role in {
        "owner",
        "admin",
        "researcher",
        "operator",
    }
    return ResponseDetailView(
        **item.model_dump(),
        methodology_version_id=response.methodology_version_id,
        current_revision=(
            _revision_detail(db, revision, response, raw_allowed) if revision else None
        ),
    )


@router.get(
    "/responses/{response_id}/revisions",
    response_model=RevisionHistoryView,
    tags=["responses"],
)
def revisions(
    response_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    response = _response(db, context, response_id)
    raw_allowed = context.membership.role in {
        "owner",
        "admin",
        "researcher",
        "operator",
    }
    rows = db.scalars(
        select(ResponseRevision)
        .where(
            ResponseRevision.tenant_id == context.organization.id,
            ResponseRevision.research_id == response.research_id,
            ResponseRevision.response_id == response.id,
        )
        .order_by(ResponseRevision.revision_number.desc())
    ).all()
    return RevisionHistoryView(
        response_id=response.id,
        current_revision_id=response.current_revision_id,
        revisions=[_revision_detail(db, row, response, raw_allowed) for row in rows],
    )


@router.get(
    "/responses/{response_id}/revisions/{revision_id}",
    response_model=RevisionDetailView,
    tags=["responses"],
)
def revision_detail(
    response_id: str,
    revision_id: str,
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    response = _response(db, context, response_id)
    revision = db.scalar(
        select(ResponseRevision).where(
            ResponseRevision.id == revision_id,
            ResponseRevision.tenant_id == context.organization.id,
            ResponseRevision.research_id == response.research_id,
            ResponseRevision.response_id == response.id,
        )
    )
    if not revision:
        raise DomainError("REVISION_NOT_FOUND", "Response revision was not found", 404)
    raw_allowed = context.membership.role in {
        "owner",
        "admin",
        "researcher",
        "operator",
    }
    return _revision_detail(db, revision, response, raw_allowed)


@router.get("/results", response_model=ResultPage, tags=["results"])
def results(
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "auditor"))
    ],
    db: Annotated[Session, Depends(get_db)],
    research_id: str | None = None,
    participant_id: str | None = None,
    response_revision_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    statement = select(Result).where(Result.tenant_id == context.organization.id)
    if research_id:
        statement = statement.where(Result.research_id == research_id)
    if participant_id:
        statement = statement.where(Result.participant_id == participant_id)
    if response_revision_id:
        statement = statement.where(Result.response_revision_id == response_revision_id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(Result.calculated_at.desc(), Result.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ResultPage(
        items=[_result_summary(db, row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/results/{result_id}/export", tags=["results"])
def export_result(
    result_id: str,
    context: Annotated[TenantContext, Depends(roles("owner", "admin", "researcher"))],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
):
    result = db.scalar(
        select(Result).where(
            Result.id == result_id, Result.tenant_id == context.organization.id
        )
    )
    if not result:
        raise DomainError("RESULT_NOT_FOUND", "Result was not found", 404)
    research = db.scalar(
        select(Research).where(
            Research.id == result.research_id,
            Research.tenant_id == context.organization.id,
        )
    )
    if not research:
        raise DomainError("RESEARCH_NOT_FOUND", "Research was not found", 404)
    _consent, licence = require_result_policy(
        db,
        tenant=context.organization,
        research=research,
        participant_id=result.participant_id,
        methodology_version_id=result.methodology_version_id,
    )
    disclosure = _effective_disclosure(licence)
    if format in {"xlsx", "pdf"}:
        audit(
            db,
            actor_id=actor.id,
            tenant_id=context.organization.id,
            research_id=research.id,
            action="result.export",
            object_type="result",
            object_id=result.id,
            outcome="failure",
            reason_code="EXPORT_FORMAT_UNSUPPORTED",
            safe_metadata={"format": format},
        )
        db.commit()
        raise DomainError(
            "EXPORT_FORMAT_UNSUPPORTED",
            f"Official {format.upper()} export is not supported in this MVP",
            415,
            details={"requested_format": format, "supported_formats": ["json", "csv"]},
        )
    audit(
        db,
        actor_id=actor.id,
        tenant_id=context.organization.id,
        research_id=research.id,
        action="result.export",
        object_type="result",
        object_id=result.id,
        safe_metadata={"format": format, "disclosure_level": disclosure},
    )
    db.commit()
    filename = f"psychogram-result-{result.id}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format == "csv":
        return PlainTextResponse(
            build_csv_export(db, result, disclosure),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    return JSONResponse(build_json_export(db, result, disclosure), headers=headers)


@router.put(
    "/researches/{research_id}/participants/{participant_id}/pii",
    response_model=PIIView,
    tags=["participants"],
)
def pii_upsert(
    research_id: str,
    participant_id: str,
    payload: PIIWrite,
    context: Annotated[TenantContext, Depends(pii_access)],
    actor: Annotated[User, Depends(current_user)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    db: Annotated[Session, Depends(get_db)],
):
    research = _research(db, context, research_id)
    participant = _participant(db, research, participant_id)
    record = upsert_pii(
        db,
        research=research,
        participant=participant,
        fields=payload.fields,
        actor_id=actor.id,
        settings=settings,
    )
    db.commit()
    return PIIView(
        participant_id=participant.id,
        fields=payload.fields,
        algorithm=record.algorithm,
        key_version=record.key_version,
        updated_at=record.updated_at,
    )


@router.get(
    "/researches/{research_id}/participants/{participant_id}/pii",
    response_model=PIIView,
    tags=["participants"],
)
def pii_get(
    research_id: str,
    participant_id: str,
    context: Annotated[TenantContext, Depends(pii_access)],
    actor: Annotated[User, Depends(current_user)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    db: Annotated[Session, Depends(get_db)],
):
    research = _research(db, context, research_id)
    participant = _participant(db, research, participant_id)
    record, fields = view_pii(
        db,
        research=research,
        participant=participant,
        actor_id=actor.id,
        settings=settings,
    )
    db.commit()
    return PIIView(
        participant_id=participant.id,
        fields=fields,
        algorithm=record.algorithm,
        key_version=record.key_version,
        updated_at=record.updated_at,
    )


@router.delete(
    "/researches/{research_id}/participants/{participant_id}/pii",
    status_code=204,
    tags=["participants"],
)
def pii_delete(
    research_id: str,
    participant_id: str,
    context: Annotated[TenantContext, Depends(pii_access)],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    research = _research(db, context, research_id)
    participant = _participant(db, research, participant_id)
    delete_pii(db, research=research, participant=participant, actor_id=actor.id)
    db.commit()
    return Response(status_code=204)


def _catalog_tenant(
    db: Session, user: User, organization_id: str | None
) -> Organization | None:
    if user.is_platform_admin and organization_id is None:
        return None
    if organization_id is None:
        raise DomainError(
            "ORGANIZATION_CONTEXT_REQUIRED",
            "X-Organization-ID is required for tenant catalogue access",
            400,
        )
    membership = db.scalar(
        select(Membership).where(
            Membership.tenant_id == organization_id,
            Membership.user_id == user.id,
            Membership.active.is_(True),
        )
    )
    tenant = db.scalar(
        select(Organization).where(
            Organization.id == organization_id, Organization.active.is_(True)
        )
    )
    if not membership or not tenant:
        raise DomainError(
            "TENANT_ACCESS_DENIED", "Active organization membership was not found", 403
        )
    return tenant


def _visible_versions(
    db: Session,
    methodology_id: str,
    user: User,
    tenant: Organization | None,
) -> list[MethodologyVersionDetailView]:
    statement = select(MethodologyVersion).where(
        MethodologyVersion.methodology_id == methodology_id
    )
    if not user.is_platform_admin:
        statement = statement.where(MethodologyVersion.lifecycle_status == "published")
    versions = db.scalars(
        statement.order_by(
            MethodologyVersion.version_code.desc(), MethodologyVersion.id.desc()
        )
    ).all()
    result = []
    for version in versions:
        licence = latest_licence(db, version.id)
        eligible = bool(tenant and _is_eligible(licence, tenant, "research"))
        if user.is_platform_admin or eligible:
            result.append(
                _version_detail(version, licence, user.is_platform_admin, eligible)
            )
    return result


def _version_detail(
    version: MethodologyVersion,
    licence: LicenceRevision | None,
    private: bool,
    eligible: bool,
) -> MethodologyVersionDetailView:
    snapshot = (
        version.snapshot if private else _redact_snapshot(version.snapshot, licence)
    )
    return MethodologyVersionDetailView(
        id=version.id,
        methodology_id=version.methodology_id,
        version_code=version.version_code,
        lifecycle_status=version.lifecycle_status,
        schema_version=version.schema_version,
        default_locale=version.default_locale,
        supported_locales=version.supported_locales,
        target_population=version.target_population,
        estimated_minutes=version.estimated_minutes,
        content_hash=version.content_hash,
        engine_contract_version=version.engine_contract_version,
        disclaimer_i18n=version.disclaimer_i18n,
        template_id=version.template_id,
        published_at=version.published_at,
        snapshot=snapshot,
        licence=(
            _licence_detail(licence, private, True, eligible) if licence else None
        ),
        eligible=eligible,
    )


def _licence_detail(
    licence: LicenceRevision,
    private: bool,
    current: bool,
    eligible: bool,
) -> LicenceDetailView:
    return LicenceDetailView(
        id=licence.id,
        methodology_version_id=licence.methodology_version_id,
        licence_revision=licence.licence_revision,
        status=licence.status,
        copyright_status=licence.copyright_status,
        rights_holder=licence.rights_holder,
        evidence_reference=licence.evidence_reference if private else None,
        allowed_use_types=licence.allowed_use_types,
        allowed_org_types=licence.allowed_org_types,
        allowed_regions=licence.allowed_regions,
        content_disclosure_level=licence.content_disclosure_level,
        allow_item_display=licence.allow_item_display,
        allow_item_export=licence.allow_item_export,
        allow_trace_item_values=licence.allow_trace_item_values,
        valid_from=licence.valid_from,
        valid_until=licence.valid_until,
        restrictions_i18n=licence.restrictions_i18n,
        change_reason=licence.change_reason if private else None,
        current=current,
        eligible=eligible,
    )


def _redact_snapshot(
    snapshot: dict[str, Any], licence: LicenceRevision | None
) -> dict[str, Any] | None:
    if not licence or licence.content_disclosure_level == "summary_only":
        return None
    items = []
    for item in snapshot.get("items", []):
        visible = {
            "item_code": item["item_code"],
            "item_type": item["item_type"],
            "required": item.get("required", True),
            "value_constraints": item.get("value_constraints", {}),
        }
        if licence.allow_item_display:
            visible["prompt_i18n"] = item.get("prompt_i18n", {})
            visible["options"] = [
                {
                    "option_code": option["option_code"],
                    "label_i18n": option.get("label_i18n", {}),
                }
                for option in item.get("options", [])
            ]
        items.append(visible)
    scales = [
        {
            key: scale.get(key)
            for key in (
                "scale_code",
                "scale_kind",
                "label_i18n",
                "unit_code",
                "theoretical_min",
                "theoretical_max",
                "display_decimals",
            )
        }
        for scale in snapshot.get("scales", [])
    ]
    return {
        "methodology_code": snapshot.get("methodology_code"),
        "version_code": snapshot.get("version_code"),
        "items": items,
        "scales": scales,
    }


def _is_eligible(
    licence: LicenceRevision | None, tenant: Organization, use_type: str
) -> bool:
    try:
        check_licence(
            licence,
            org_type=tenant.org_type,
            region=tenant.region,
            use_type=use_type,
        )
        return True
    except DomainError:
        return False


def _research(db: Session, context: TenantContext, research_id: str) -> Research:
    research = db.scalar(
        select(Research).where(
            Research.id == research_id,
            Research.tenant_id == context.organization.id,
        )
    )
    if not research:
        raise DomainError("RESEARCH_NOT_FOUND", "Research was not found", 404)
    return research


def _participant(db: Session, research: Research, participant_id: str) -> Participant:
    participant = db.scalar(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.tenant_id == research.tenant_id,
            Participant.research_id == research.id,
        )
    )
    if not participant:
        raise DomainError("PARTICIPANT_NOT_FOUND", "Participant was not found", 404)
    return participant


def _participant_item(db: Session, participant: Participant) -> ParticipantListItem:
    consent = db.scalar(
        select(ConsentRecord)
        .where(
            ConsentRecord.tenant_id == participant.tenant_id,
            ConsentRecord.research_id == participant.research_id,
            ConsentRecord.participant_id == participant.id,
        )
        .order_by(ConsentRecord.record_version.desc())
    )
    has_pii = bool(
        db.scalar(
            select(func.count(ParticipantPII.id)).where(
                ParticipantPII.tenant_id == participant.tenant_id,
                ParticipantPII.participant_id == participant.id,
            )
        )
    )
    return ParticipantListItem(
        id=participant.id,
        research_id=participant.research_id,
        external_code=participant.external_code,
        processing_status=participant.processing_status,
        created_at=participant.created_at,
        current_consent_status=consent.status if consent else None,
        has_pii=has_pii,
    )


def _response(db: Session, context: TenantContext, response_id: str) -> ResponseModel:
    response = db.scalar(
        select(ResponseModel).where(
            ResponseModel.id == response_id,
            ResponseModel.tenant_id == context.organization.id,
        )
    )
    if not response:
        raise DomainError("RESPONSE_NOT_FOUND", "Response was not found", 404)
    return response


def _response_item(db: Session, response: ResponseModel) -> ResponseListItem:
    participant = db.get(Participant, response.participant_id)
    revision = (
        db.get(ResponseRevision, response.current_revision_id)
        if response.current_revision_id
        else None
    )
    return ResponseListItem(
        id=response.id,
        research_id=response.research_id,
        participant_id=response.participant_id,
        participant_external_code=participant.external_code if participant else "",
        attempt_key=response.attempt_key,
        status=response.status,
        lock_version=response.lock_version,
        current_revision_id=response.current_revision_id,
        current_revision_number=revision.revision_number if revision else None,
        current_revision_status=revision.status if revision else None,
        created_at=response.created_at,
    )


def _revision_detail(
    db: Session,
    revision: ResponseRevision,
    response: ResponseModel,
    raw_allowed: bool,
) -> RevisionDetailView:
    return RevisionDetailView(
        id=revision.id,
        response_id=revision.response_id,
        revision_number=revision.revision_number,
        status=revision.status,
        answer_payload_hash=revision.answer_payload_hash,
        validation_summary=revision.validation_summary,
        source_type=revision.source_type,
        correction_reason=revision.correction_reason,
        created_at=revision.created_at,
        created_by=revision.created_by,
        validated_at=revision.validated_at,
        validated_by=revision.validated_by,
        answers=revision.answers if raw_allowed else None,
        is_current=response.current_revision_id == revision.id,
        validation_issues=[
            ValidationIssueView.model_validate(issue)
            for issue in validation_issues(db, revision.id)
        ],
    )


def _result_summary(db: Session, result: Result) -> ResultSummaryView:
    scales = db.scalars(
        select(ScaleResult)
        .where(ScaleResult.result_id == result.id)
        .order_by(ScaleResult.scale_code.asc())
    ).all()
    return ResultSummaryView(
        id=result.id,
        research_id=result.research_id,
        participant_id=result.participant_id,
        response_id=result.response_id,
        response_revision_id=result.response_revision_id,
        status=result.status,
        calculated_at=result.calculated_at,
        result_hash=result.result_hash,
        disclaimer_i18n=result.disclaimer_i18n_snapshot,
        scales=[
            ScaleResultView(
                scale_code=scale.scale_code,
                validity_status=scale.validity_status,
                reason_codes=scale.reason_codes,
                answered_count=scale.answered_count,
                missing_count=scale.missing_count,
                aggregate_score_unrounded=scale.aggregate_score_unrounded,
                score_unrounded=scale.score_unrounded,
                score_display=scale.score_display,
                unit_code=scale.unit_code,
                norm_band_code=scale.norm_band_code,
                interpretation_code=scale.interpretation_code,
                interpretation_snapshot_i18n=scale.interpretation_snapshot_i18n,
                disclosure_level_applied=scale.disclosure_level_applied,
            )
            for scale in scales
        ],
    )
