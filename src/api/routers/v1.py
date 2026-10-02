from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import (
    TenantContext,
    current_user,
    get_db,
    get_runtime_settings,
    platform_admin,
    roles,
    tenant_context,
)
from src.core.config import Settings
from src.core.errors import DomainError
from src.models.domain import (
    AuditEvent,
    ImportJob,
    Membership,
    Methodology,
    MethodologyVersion,
    Participant,
    Research,
    Response,
    ResponseRevision,
    Result,
    RetentionPolicy,
    User,
)
from src.schemas.api import (
    CSVPreviewRequest,
    CalculationRequest,
    ConsentCreate,
    ConsentView,
    ImportConfirmRequest,
    ImportConfirmView,
    ImportPreviewView,
    LicenceCreate,
    LicenceView,
    MemberCreate,
    MemberView,
    MethodologyCreate,
    MethodologyVersionCreate,
    MethodologyVersionView,
    MethodologyView,
    OrganizationView,
    ParticipantCreate,
    ParticipantView,
    PublishRequest,
    RegisterRequest,
    ResearchCreate,
    ResearchView,
    ResponseCreate,
    ResponseView,
    ResultView,
    RetentionPolicyCreate,
    RevisionCreate,
    RevisionView,
    ValidationIssueView,
)
from src.services.domain import (
    activate_research,
    add_member,
    create_participant,
    create_research,
    create_response,
    record_consent,
    register_owner,
    revise_response,
    validate_revision,
    validation_issues,
)
from src.services.imports import confirm_import, preview_csv
from src.services.orchestration import (
    calculate,
    require_result_policy,
    result_view,
)
from src.services.registry import (
    create_licence,
    create_methodology,
    create_version,
    publish_version,
)

router = APIRouter(prefix="/api/v1")


@router.get(
    "/organizations/current", response_model=OrganizationView, tags=["organizations"]
)
def current_organization(context: Annotated[TenantContext, Depends(tenant_context)]):
    return context.organization


@router.post(
    "/organizations",
    response_model=OrganizationView,
    status_code=201,
    tags=["organizations"],
)
def organization_create(
    payload: RegisterRequest,
    actor: Annotated[User, Depends(platform_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    _owner, organization = register_owner(db, payload, actor_id=actor.id)
    db.commit()
    db.refresh(organization)
    return organization


@router.get(
    "/organizations/current/members",
    response_model=list[MemberView],
    tags=["organizations"],
)
def list_members(
    context: Annotated[TenantContext, Depends(roles("owner", "admin"))],
    db: Annotated[Session, Depends(get_db)],
):
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.tenant_id == context.organization.id)
    ).all()
    return [
        MemberView(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            can_view_pii=member.can_view_pii,
            active=member.active,
        )
        for member, user in rows
    ]


@router.post(
    "/organizations/current/members",
    response_model=MemberView,
    status_code=201,
    tags=["organizations"],
)
def create_member(
    payload: MemberCreate,
    context: Annotated[TenantContext, Depends(roles("owner", "admin"))],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    user, member = add_member(db, context.organization.id, payload, actor.id)
    db.commit()
    return MemberView(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        can_view_pii=member.can_view_pii,
        active=member.active,
    )


@router.post("/retention-policies", status_code=201, tags=["research"])
def create_retention_policy(
    payload: RetentionPolicyCreate,
    context: Annotated[TenantContext, Depends(roles("owner", "admin"))],
    db: Annotated[Session, Depends(get_db)],
):
    if db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.tenant_id == context.organization.id,
            RetentionPolicy.code == payload.code,
        )
    ):
        raise DomainError(
            "RETENTION_POLICY_CODE_EXISTS", "Retention policy code already exists", 409
        )
    policy = RetentionPolicy(
        tenant_id=context.organization.id,
        code=payload.code,
        retention_days=payload.retention_days,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {
        "id": policy.id,
        "code": policy.code,
        "retention_days": policy.retention_days,
    }


@router.get(
    "/methodologies", response_model=list[MethodologyView], tags=["methodologies"]
)
def list_methodologies(
    _user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.scalars(select(Methodology).order_by(Methodology.methodology_code)).all()


@router.post(
    "/methodologies",
    response_model=MethodologyView,
    status_code=201,
    tags=["methodologies"],
)
def methodology_create(
    payload: MethodologyCreate,
    actor: Annotated[User, Depends(platform_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    methodology = create_methodology(db, payload, actor.id)
    db.commit()
    db.refresh(methodology)
    return methodology


@router.post(
    "/methodologies/{methodology_id}/versions",
    response_model=MethodologyVersionView,
    status_code=201,
    tags=["methodologies"],
)
def methodology_version_create(
    methodology_id: str,
    payload: MethodologyVersionCreate,
    actor: Annotated[User, Depends(platform_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    methodology = db.get(Methodology, methodology_id)
    if not methodology:
        raise DomainError("METHODOLOGY_NOT_FOUND", "Methodology was not found", 404)
    version = create_version(db, methodology, payload, actor.id)
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/methodology-versions/{version_id}/licences",
    response_model=LicenceView,
    status_code=201,
    tags=["methodologies"],
)
def licence_create(
    version_id: str,
    payload: LicenceCreate,
    actor: Annotated[User, Depends(platform_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    version = db.get(MethodologyVersion, version_id)
    if not version:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    licence = create_licence(db, version, payload, actor.id)
    db.commit()
    db.refresh(licence)
    return licence


@router.post(
    "/methodology-versions/{version_id}/publish",
    response_model=MethodologyVersionView,
    tags=["methodologies"],
)
def methodology_publish(
    version_id: str,
    payload: PublishRequest,
    actor: Annotated[User, Depends(platform_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    version = db.get(MethodologyVersion, version_id)
    if not version:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version was not found", 404
        )
    publish_version(db, version, actor.id, payload.reason)
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/researches", response_model=ResearchView, status_code=201, tags=["research"]
)
def research_create(
    payload: ResearchCreate,
    context: Annotated[TenantContext, Depends(roles("owner", "admin", "researcher"))],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    research = create_research(db, context.organization, payload, actor.id)
    db.commit()
    db.refresh(research)
    return research


@router.get("/researches", response_model=list[ResearchView], tags=["research"])
def researches(
    context: Annotated[TenantContext, Depends(tenant_context)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.scalars(
        select(Research)
        .where(Research.tenant_id == context.organization.id)
        .order_by(Research.created_at)
    ).all()


@router.post(
    "/researches/{research_id}/activate", response_model=ResearchView, tags=["research"]
)
def research_activate(
    research_id: str,
    context: Annotated[TenantContext, Depends(roles("owner", "admin", "researcher"))],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    research = _research(db, context, research_id)
    activate_research(db, context.organization, research, actor.id)
    db.commit()
    db.refresh(research)
    return research


@router.post(
    "/researches/{research_id}/participants",
    response_model=ParticipantView,
    status_code=201,
    tags=["participants"],
)
def participant_create(
    research_id: str,
    payload: ParticipantCreate,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    participant = create_participant(
        db, _research(db, context, research_id), payload, actor.id
    )
    db.commit()
    db.refresh(participant)
    return participant


@router.post(
    "/participants/{participant_id}/consents",
    response_model=ConsentView,
    status_code=201,
    tags=["participants"],
)
def consent_create(
    participant_id: str,
    payload: ConsentCreate,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    participant = db.scalar(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.tenant_id == context.organization.id,
        )
    )
    if not participant:
        raise DomainError("PARTICIPANT_NOT_FOUND", "Participant was not found", 404)
    consent = record_consent(db, participant, payload, actor.id)
    db.commit()
    db.refresh(consent)
    return consent


@router.post(
    "/researches/{research_id}/responses",
    response_model=ResponseView,
    status_code=201,
    tags=["responses"],
)
def response_create(
    research_id: str,
    payload: ResponseCreate,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    response, _revision = create_response(
        db, _research(db, context, research_id), payload, actor.id
    )
    db.commit()
    db.refresh(response)
    return response


@router.post(
    "/responses/{response_id}/revisions",
    response_model=RevisionView,
    status_code=201,
    tags=["responses"],
)
def response_revise(
    response_id: str,
    payload: RevisionCreate,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    response = _response(db, context, response_id)
    revision = revise_response(db, response, payload, actor.id)
    db.commit()
    db.refresh(revision)
    return _revision_view(db, revision)


@router.post(
    "/responses/{response_id}/validate", response_model=RevisionView, tags=["responses"]
)
def response_validate(
    response_id: str,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    response = _response(db, context, response_id)
    revision = db.get(ResponseRevision, response.current_revision_id)
    if not revision:
        raise DomainError("REVISION_NOT_FOUND", "Current revision was not found", 404)
    validate_revision(db, response, revision, actor.id)
    db.commit()
    db.refresh(revision)
    return _revision_view(db, revision)


@router.post(
    "/researches/{research_id}/calculations",
    response_model=ResultView,
    tags=["results"],
)
def calculate_result(
    research_id: str,
    payload: CalculationRequest,
    context: Annotated[TenantContext, Depends(roles("owner", "admin", "researcher"))],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    result = calculate(
        db,
        tenant=context.organization,
        research=_research(db, context, research_id),
        revision_id=payload.response_revision_id,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
    )
    db.commit()
    return result_view(db, result)


@router.get("/results/{result_id}", response_model=ResultView, tags=["results"])
def get_result(
    result_id: str,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "auditor"))
    ],
    db: Annotated[Session, Depends(get_db)],
):
    result = db.scalar(
        select(Result).where(
            Result.id == result_id, Result.tenant_id == context.organization.id
        )
    )
    if not result:
        raise DomainError("RESULT_NOT_FOUND", "Result was not found", 404)
    require_result_policy(
        db,
        tenant=context.organization,
        research=_research(db, context, result.research_id),
        participant_id=result.participant_id,
        methodology_version_id=result.methodology_version_id,
    )
    return result_view(db, result)


@router.post(
    "/researches/{research_id}/imports/preview",
    response_model=ImportPreviewView,
    status_code=201,
    tags=["imports"],
)
def import_preview(
    research_id: str,
    payload: CSVPreviewRequest,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    db: Annotated[Session, Depends(get_db)],
):
    job, errors = preview_csv(
        db,
        research=_research(db, context, research_id),
        csv_text=payload.csv_text,
        actor_id=actor.id,
        max_bytes=settings.max_csv_bytes,
        max_rows=settings.max_csv_rows,
    )
    db.commit()
    return ImportPreviewView(
        import_id=job.id,
        status=job.status,
        preview_hash=job.preview_hash,
        summary=job.summary,
        errors=errors,
    )


@router.post(
    "/researches/{research_id}/imports/{import_id}/confirm",
    response_model=ImportConfirmView,
    tags=["imports"],
)
def import_confirm(
    research_id: str,
    import_id: str,
    payload: ImportConfirmRequest,
    context: Annotated[
        TenantContext, Depends(roles("owner", "admin", "researcher", "operator"))
    ],
    actor: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    research = _research(db, context, research_id)
    job = db.scalar(
        select(ImportJob).where(
            ImportJob.id == import_id, ImportJob.tenant_id == context.organization.id
        )
    )
    if not job:
        raise DomainError("IMPORT_NOT_FOUND", "Import job was not found", 404)
    confirm_import(
        db,
        job=job,
        research=research,
        preview_hash=payload.preview_hash,
        actor_id=actor.id,
    )
    db.commit()
    return ImportConfirmView(import_id=job.id, status=job.status, summary=job.summary)


@router.get("/audit-events", tags=["audit"])
def audit_events(
    context: Annotated[TenantContext, Depends(roles("owner", "admin", "auditor"))],
    db: Annotated[Session, Depends(get_db)],
):
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == context.organization.id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(200)
    ).all()
    return [
        {
            "id": row.id,
            "occurred_at": row.occurred_at,
            "actor_id": row.actor_id,
            "research_id": row.research_id,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "action": row.action,
            "outcome": row.outcome,
            "reason_code": row.reason_code,
            "safe_metadata": row.safe_metadata,
        }
        for row in rows
    ]


def _research(db: Session, context: TenantContext, research_id: str) -> Research:
    research = db.scalar(
        select(Research).where(
            Research.id == research_id, Research.tenant_id == context.organization.id
        )
    )
    if not research:
        raise DomainError("RESEARCH_NOT_FOUND", "Research was not found", 404)
    return research


def _revision_view(db: Session, revision: ResponseRevision) -> RevisionView:
    return RevisionView.model_validate(revision).model_copy(
        update={
            "validation_issues": [
                ValidationIssueView.model_validate(issue)
                for issue in validation_issues(db, revision.id)
            ]
        }
    )


def _response(db: Session, context: TenantContext, response_id: str) -> Response:
    response = db.scalar(
        select(Response).where(
            Response.id == response_id, Response.tenant_id == context.organization.id
        )
    )
    if not response:
        raise DomainError("RESPONSE_NOT_FOUND", "Response was not found", 404)
    return response
