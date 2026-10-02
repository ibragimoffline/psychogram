from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import DomainError
from src.core.security import hash_password, verify_password
from src.models.domain import (
    ConsentRecord,
    Membership,
    MethodologyVersion,
    NormSet,
    Organization,
    Participant,
    Research,
    ResearchMethodologyPin,
    Response,
    ResponseRevision,
    ResponseValidationIssue,
    RetentionPolicy,
    Scale,
    User,
)
from src.schemas.api import (
    BootstrapRequest,
    ConsentCreate,
    MemberCreate,
    ParticipantCreate,
    RegisterRequest,
    ResearchCreate,
    ResponseCreate,
    RevisionCreate,
)
from src.services.audit import audit
from src.services.registry import check_licence, latest_licence
from src.services.scoring_engine import validate_answers


def canonical_answer_hash(answers: dict) -> str:
    encoded = json.dumps(
        answers, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def bootstrap_user(
    db: Session,
    payload: BootstrapRequest,
    configured_token: str,
    *,
    enabled: bool,
) -> User:
    if not enabled:
        raise DomainError("BOOTSTRAP_DISABLED", "Bootstrap is disabled", 404)
    provided = payload.bootstrap_token or ""
    provided_digest = hashlib.sha256(provided.encode()).digest()
    configured_digest = hashlib.sha256(configured_token.encode()).digest()
    if not secrets.compare_digest(provided_digest, configured_digest):
        raise DomainError("BOOTSTRAP_TOKEN_INVALID", "Bootstrap token is invalid", 403)
    if db.scalar(select(func.count(User.id))):
        raise DomainError(
            "BOOTSTRAP_ALREADY_COMPLETED",
            "Bootstrap can only run on an empty database",
            409,
        )
    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_platform_admin=True,
    )
    db.add(user)
    db.flush()
    audit(
        db,
        actor_id=user.id,
        action="auth.bootstrap",
        object_type="user",
        object_id=user.id,
    )
    return user


def register_owner(
    db: Session, payload: RegisterRequest, *, actor_id: str | None = None
) -> tuple[User, Organization]:
    """Create an organization with its owner; actor_id is set when an admin does it."""
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise DomainError(
            "EMAIL_ALREADY_REGISTERED", "Email is already registered", 409
        )
    if db.scalar(
        select(Organization).where(Organization.code == payload.organization_code)
    ):
        raise DomainError(
            "ORGANIZATION_CODE_EXISTS", "Organization code already exists", 409
        )
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    organization = Organization(
        code=payload.organization_code,
        name=payload.organization_name.strip(),
        org_type=payload.org_type,
        region=payload.region,
    )
    db.add_all([user, organization])
    db.flush()
    db.add(
        Membership(
            tenant_id=organization.id, user_id=user.id, role="owner", can_view_pii=True
        )
    )
    audit(
        db,
        actor_id=actor_id or user.id,
        action="organization.create" if actor_id else "organization.register",
        object_type="organization",
        object_id=organization.id,
        tenant_id=organization.id,
    )
    return user, organization


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not user.active or not verify_password(password, user.password_hash):
        audit(
            db,
            actor_id=user.id if user else None,
            action="auth.login",
            object_type="user",
            object_id=user.id if user else None,
            outcome="failure",
            reason_code="AUTH_CREDENTIALS_INVALID",
        )
        raise DomainError(
            "AUTH_CREDENTIALS_INVALID", "Email or password is invalid", 401
        )
    audit(
        db, actor_id=user.id, action="auth.login", object_type="user", object_id=user.id
    )
    return user


def add_member(
    db: Session, tenant_id: str, payload: MemberCreate, actor_id: str
) -> tuple[User, Membership]:
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            email=email,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.flush()
    existing = db.scalar(
        select(Membership).where(
            Membership.tenant_id == tenant_id, Membership.user_id == user.id
        )
    )
    if existing:
        raise DomainError("MEMBERSHIP_EXISTS", "User is already a member", 409)
    membership = Membership(
        tenant_id=tenant_id,
        user_id=user.id,
        role=payload.role,
        can_view_pii=payload.can_view_pii,
    )
    db.add(membership)
    audit(
        db,
        actor_id=actor_id,
        tenant_id=tenant_id,
        action="membership.create",
        object_type="membership",
        object_id=membership.id,
        safe_metadata={"role": payload.role, "can_view_pii": payload.can_view_pii},
    )
    return user, membership


def create_research(
    db: Session, tenant: Organization, payload: ResearchCreate, actor_id: str
) -> Research:
    version = db.get(MethodologyVersion, payload.methodology_version_id)
    if (
        not version
        or version.lifecycle_status != "published"
        or not version.content_hash
    ):
        raise DomainError(
            "METHODOLOGY_NOT_PUBLISHED",
            "Research requires a published methodology version",
            409,
        )
    policy = db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.id == payload.retention_policy_id,
            RetentionPolicy.tenant_id == tenant.id,
            RetentionPolicy.active.is_(True),
        )
    )
    if not policy:
        raise DomainError(
            "RETENTION_POLICY_NOT_FOUND",
            "Retention policy is outside the active organization",
            404,
        )
    check_licence(
        latest_licence(db, version.id),
        org_type=tenant.org_type,
        region=tenant.region,
        use_type=payload.use_type,
    )
    research = Research(
        tenant_id=tenant.id,
        name=payload.name,
        purpose=payload.purpose,
        status="ready",
        methodology_version_id=version.id,
        pii_mode=payload.pii_mode,
        consent_reference=payload.consent_reference,
        consent_version=payload.consent_version,
        retention_policy_id=policy.id,
        responsible_user_id=actor_id,
        use_type=payload.use_type,
        created_by=actor_id,
    )
    db.add(research)
    db.flush()
    selection = dict(payload.norm_selection)
    if not selection:
        default_norms = db.execute(
            select(Scale.scale_code, NormSet.id)
            .join(NormSet, NormSet.scale_id == Scale.id)
            .where(
                Scale.methodology_version_id == version.id,
                NormSet.methodology_version_id == version.id,
                NormSet.is_default.is_(True),
            )
        ).all()
        selection = {scale_code: norm_id for scale_code, norm_id in default_norms}
    for scale_code, norm_id in selection.items():
        norm = db.scalar(
            select(NormSet).where(
                NormSet.id == norm_id, NormSet.methodology_version_id == version.id
            )
        )
        if not norm:
            raise DomainError(
                "NORM_PIN_INVALID",
                f"Norm for scale '{scale_code}' does not belong to the version",
            )
    db.add(
        ResearchMethodologyPin(
            tenant_id=tenant.id,
            research_id=research.id,
            methodology_version_id=version.id,
            methodology_content_hash=version.content_hash,
            norm_selection=selection,
            pinned_by=actor_id,
        )
    )
    audit(
        db,
        actor_id=actor_id,
        tenant_id=tenant.id,
        research_id=research.id,
        action="research.create",
        object_type="research",
        object_id=research.id,
    )
    return research


def activate_research(
    db: Session, tenant: Organization, research: Research, actor_id: str
) -> Research:
    if research.tenant_id != tenant.id:
        raise DomainError(
            "TENANT_ACCESS_DENIED",
            "Research does not belong to the active organization",
            404,
        )
    if research.status == "active":
        return research
    if research.status != "ready":
        raise DomainError(
            "RESEARCH_STATE_INVALID", "Only ready research can be activated", 409
        )
    version = db.get(MethodologyVersion, research.methodology_version_id)
    if not version or version.lifecycle_status != "published":
        raise DomainError(
            "METHODOLOGY_NOT_PUBLISHED", "Pinned version is not published", 409
        )
    check_licence(
        latest_licence(db, version.id),
        org_type=tenant.org_type,
        region=tenant.region,
        use_type=research.use_type,
    )
    research.status = "active"
    audit(
        db,
        actor_id=actor_id,
        tenant_id=tenant.id,
        research_id=research.id,
        action="research.activate",
        object_type="research",
        object_id=research.id,
    )
    return research


def create_participant(
    db: Session, research: Research, payload: ParticipantCreate, actor_id: str
) -> Participant:
    if research.status != "active":
        raise DomainError(
            "RESEARCH_NOT_ACTIVE",
            "Participants can only be added to active research",
            409,
        )
    if payload.pii:
        raise DomainError(
            "PII_STORAGE_NOT_CONFIGURED",
            "Direct PII storage is disabled in this MVP deployment",
            409,
        )
    if db.scalar(
        select(Participant).where(
            Participant.tenant_id == research.tenant_id,
            Participant.research_id == research.id,
            Participant.external_code == payload.external_code,
        )
    ):
        raise DomainError(
            "PARTICIPANT_CODE_EXISTS",
            "Participant code already exists in this research",
            409,
        )
    participant = Participant(
        tenant_id=research.tenant_id,
        research_id=research.id,
        external_code=payload.external_code,
        created_by=actor_id,
    )
    db.add(participant)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="participant.create",
        object_type="participant",
        object_id=participant.id,
    )
    return participant


def record_consent(
    db: Session, participant: Participant, payload: ConsentCreate, actor_id: str
) -> ConsentRecord:
    if payload.status == "not_required_with_basis" and not payload.basis:
        raise DomainError(
            "CONSENT_BASIS_REQUIRED", "A basis is required for not_required_with_basis"
        )
    latest_version = (
        db.scalar(
            select(func.max(ConsentRecord.record_version)).where(
                ConsentRecord.participant_id == participant.id
            )
        )
        or 0
    )
    consent = ConsentRecord(
        tenant_id=participant.tenant_id,
        research_id=participant.research_id,
        participant_id=participant.id,
        status=payload.status,
        reference=payload.reference,
        version=payload.version,
        obtained_at=payload.obtained_at,
        recorded_by=actor_id,
        basis=payload.basis,
        record_version=latest_version + 1,
    )
    db.add(consent)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        tenant_id=participant.tenant_id,
        research_id=participant.research_id,
        action="consent.record",
        object_type="consent",
        object_id=consent.id,
        safe_metadata={
            "status": payload.status,
            "record_version": consent.record_version,
        },
    )
    return consent


def latest_consent(db: Session, participant_id: str) -> ConsentRecord | None:
    return db.scalar(
        select(ConsentRecord)
        .where(ConsentRecord.participant_id == participant_id)
        .order_by(ConsentRecord.record_version.desc())
    )


def require_valid_consent(db: Session, participant_id: str) -> ConsentRecord:
    consent = latest_consent(db, participant_id)
    if (
        not consent
        or consent.status not in {"granted", "not_required_with_basis"}
        or consent.status == "not_required_with_basis"
        and not consent.basis
    ):
        raise DomainError("CONSENT_NOT_VALID", "Participant consent is not valid", 409)
    return consent


def create_response(
    db: Session, research: Research, payload: ResponseCreate, actor_id: str
) -> tuple[Response, ResponseRevision]:
    if research.status != "active":
        raise DomainError(
            "RESEARCH_NOT_ACTIVE", "Responses require active research", 409
        )
    participant = db.scalar(
        select(Participant).where(
            Participant.id == payload.participant_id,
            Participant.tenant_id == research.tenant_id,
            Participant.research_id == research.id,
            Participant.processing_status == "active",
        )
    )
    if not participant:
        raise DomainError(
            "PARTICIPANT_NOT_FOUND", "Participant was not found in this research", 404
        )
    require_valid_consent(db, participant.id)
    existing = db.scalar(
        select(Response).where(
            Response.tenant_id == research.tenant_id,
            Response.research_id == research.id,
            Response.participant_id == participant.id,
            Response.attempt_key == payload.attempt_key,
        )
    )
    if existing:
        raise DomainError(
            "RESPONSE_ATTEMPT_EXISTS", "Response attempt already exists", 409
        )
    response = Response(
        tenant_id=research.tenant_id,
        research_id=research.id,
        participant_id=participant.id,
        attempt_key=payload.attempt_key,
        methodology_version_id=research.methodology_version_id,
        created_by=actor_id,
    )
    db.add(response)
    db.flush()
    revision = _new_revision(
        db, response, payload.answers, actor_id, "manual", None, payload.finalize
    )
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="response.create",
        object_type="response",
        object_id=response.id,
        safe_metadata={"revision_number": 1, "finalized": payload.finalize},
    )
    return response, revision


def revise_response(
    db: Session, response: Response, payload: RevisionCreate, actor_id: str
) -> ResponseRevision:
    if response.lock_version != payload.expected_lock_version:
        raise DomainError(
            "REVISION_CONFLICT", "Response was modified by another actor", 409
        )
    current = (
        db.get(ResponseRevision, response.current_revision_id)
        if response.current_revision_id
        else None
    )
    if not current:
        raise DomainError("REVISION_NOT_FOUND", "Current revision is missing", 409)
    revision = _new_revision(
        db,
        response,
        payload.answers,
        actor_id,
        "manual",
        payload.correction_reason,
        payload.finalize,
    )
    response.lock_version += 1
    audit(
        db,
        actor_id=actor_id,
        tenant_id=response.tenant_id,
        research_id=response.research_id,
        action="response.revise",
        object_type="response",
        object_id=response.id,
        safe_metadata={"revision_number": revision.revision_number},
    )
    return revision


def _new_revision(
    db: Session,
    response: Response,
    answers: dict,
    actor_id: str,
    source_type: str,
    correction_reason: str | None,
    finalize: bool,
) -> ResponseRevision:
    version = db.get(MethodologyVersion, response.methodology_version_id)
    if not version:
        raise DomainError(
            "METHODOLOGY_VERSION_NOT_FOUND", "Methodology version is missing", 409
        )
    number = (
        db.scalar(
            select(func.max(ResponseRevision.revision_number)).where(
                ResponseRevision.response_id == response.id
            )
        )
        or 0
    )
    normalized = {key: answers[key] for key in sorted(answers)}
    revision = ResponseRevision(
        tenant_id=response.tenant_id,
        research_id=response.research_id,
        response_id=response.id,
        revision_number=number + 1,
        answers=normalized,
        answer_payload_hash=canonical_answer_hash(normalized),
        status="draft",
        validation_summary={"error_count": 0, "validator_version": "response/1"},
        source_type=source_type,
        correction_reason=correction_reason,
        created_by=actor_id,
    )
    db.add(revision)
    db.flush()
    response.current_revision_id = revision.id
    response.status = "draft"
    if finalize:
        validate_revision(db, response, revision, actor_id)
    return revision


def validation_issues(db: Session, revision_id: str) -> list[ResponseValidationIssue]:
    return list(
        db.scalars(
            select(ResponseValidationIssue)
            .where(ResponseValidationIssue.response_revision_id == revision_id)
            .order_by(
                ResponseValidationIssue.item_code, ResponseValidationIssue.error_code
            )
        ).all()
    )


def validate_revision(
    db: Session, response: Response, revision: ResponseRevision, actor_id: str
) -> ResponseRevision:
    if response.current_revision_id != revision.id:
        raise DomainError(
            "REVISION_NOT_CURRENT", "Only the current revision can be validated", 409
        )
    # Answers and snapshot are immutable, so the outcome is final; re-running would only
    # duplicate the stored issues.
    if revision.status in {"validated", "validation_failed"}:
        return revision
    require_valid_consent(db, response.participant_id)
    version = db.get(MethodologyVersion, response.methodology_version_id)
    issues = (
        validate_answers(version.snapshot, revision.answers)
        if version
        else [
            {
                "error_code": "METHODOLOGY_VERSION_NOT_FOUND",
                "item_code": None,
                "safe_params": {},
            }
        ]
    )
    for issue in issues:
        db.add(
            ResponseValidationIssue(
                response_revision_id=revision.id,
                item_code=issue.get("item_code"),
                error_code=issue["error_code"],
                safe_params=issue.get("safe_params", {}),
            )
        )
    revision.validation_summary = {
        "error_count": len(issues),
        "validator_version": "response/1",
    }
    if issues:
        revision.status = "validation_failed"
        response.status = "validation_failed"
    else:
        revision.status = "validated"
        revision.validated_at = datetime.now(UTC)
        revision.validated_by = actor_id
        response.status = "validated"
    audit(
        db,
        actor_id=actor_id,
        tenant_id=response.tenant_id,
        research_id=response.research_id,
        action="response.validate",
        object_type="response_revision",
        object_id=revision.id,
        outcome="success" if not issues else "failure",
        reason_code=issues[0]["error_code"] if issues else None,
        safe_metadata={"error_count": len(issues)},
    )
    return revision
