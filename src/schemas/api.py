from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BootstrapRequest(APIModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=200)
    bootstrap_token: str | None = None


class RegisterRequest(APIModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)
    organization_code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    org_type: str = "research_center"
    region: str = "GLOBAL"


class LoginRequest(APIModel):
    email: EmailStr
    password: str


class TokenResponse(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class MembershipView(APIModel):
    organization_id: str
    organization_name: str
    role: str
    can_view_pii: bool


class MeResponse(APIModel):
    id: str
    email: str
    full_name: str
    is_platform_admin: bool
    memberships: list[MembershipView]


class OrganizationView(APIModel):
    id: str
    code: str
    name: str
    org_type: str
    region: str


class MemberCreate(APIModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=200)
    role: Literal["admin", "researcher", "operator", "auditor"]
    can_view_pii: bool = False


class MemberView(APIModel):
    user_id: str
    email: str
    full_name: str
    role: str
    can_view_pii: bool
    active: bool


class MethodologyCreate(APIModel):
    methodology_code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    canonical_name: str = Field(min_length=1, max_length=200)
    purpose_summary: str = Field(min_length=1, max_length=2000)
    owner_name: str = Field(min_length=1, max_length=300)
    source_reference: str = Field(min_length=1, max_length=1000)


class MethodologyView(APIModel):
    id: str
    methodology_code: str
    canonical_name: str
    catalog_status: str


class MethodologyVersionCreate(APIModel):
    version_code: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    default_locale: str = "uz-Latn"
    supported_locales: list[str] = Field(
        default_factory=lambda: ["uz-Latn"], min_length=1
    )
    target_population: dict[str, Any] = Field(
        default_factory=lambda: {"adults_only": True, "min_age": 18}
    )
    estimated_minutes: int = Field(ge=1, le=1440)
    disclaimer_i18n: dict[str, str] = Field(
        default_factory=lambda: {"uz-Latn": "Bu natija tibbiy tashxis emas."}
    )
    snapshot: dict[str, Any]


class MethodologyVersionView(APIModel):
    id: str
    methodology_id: str
    version_code: str
    lifecycle_status: str
    content_hash: str | None
    template_id: str


class LicenceCreate(APIModel):
    status: Literal["verified", "restricted", "expired", "revoked", "unknown"]
    copyright_status: Literal[
        "copyrighted", "public_domain", "permission_granted", "unknown"
    ]
    rights_holder: str = Field(min_length=1, max_length=300)
    evidence_reference: str = Field(min_length=1, max_length=1000)
    allowed_use_types: list[Literal["research", "education", "clinical"]] = Field(
        min_length=1
    )
    allowed_org_types: list[str] = Field(min_length=1)
    allowed_regions: list[str] = Field(min_length=1)
    content_disclosure_level: Literal["full", "derived_only", "summary_only"]
    allow_item_display: bool = False
    allow_item_export: bool = False
    allow_trace_item_values: bool = False
    valid_from: date
    valid_until: date | None = None
    required_disclaimer_i18n: dict[str, str]
    restrictions_i18n: dict[str, str]
    change_reason: str = Field(min_length=1, max_length=2000)


class LicenceView(APIModel):
    id: str
    methodology_version_id: str
    licence_revision: int
    status: str
    content_disclosure_level: str


class PublishRequest(APIModel):
    reason: str = Field(min_length=1, max_length=2000)


class RetentionPolicyCreate(APIModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    retention_days: int = Field(ge=1, le=36500)


class ResearchCreate(APIModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2000)
    methodology_version_id: str
    pii_mode: Literal["anonymous", "pseudonymous", "identified"] = "pseudonymous"
    consent_reference: str = Field(min_length=1, max_length=1000)
    consent_version: str = Field(min_length=1, max_length=64)
    retention_policy_id: str
    norm_selection: dict[str, str] = Field(default_factory=dict)
    use_type: Literal["research", "education", "clinical"] = "research"


class ResearchView(APIModel):
    id: str
    tenant_id: str
    name: str
    purpose: str
    status: str
    methodology_version_id: str
    pii_mode: str
    use_type: Literal["research", "education", "clinical"]


class ParticipantCreate(APIModel):
    external_code: str = Field(min_length=1, max_length=120)
    pii: dict[str, str] | None = None


class ParticipantView(APIModel):
    id: str
    research_id: str
    external_code: str
    processing_status: str


class ConsentCreate(APIModel):
    status: Literal["granted", "withdrawn", "declined", "not_required_with_basis"]
    reference: str = Field(min_length=1, max_length=1000)
    version: str = Field(min_length=1, max_length=64)
    obtained_at: datetime
    basis: str | None = None


class ConsentView(APIModel):
    id: str
    participant_id: str
    status: str
    reference: str
    version: str
    record_version: int


class ResponseCreate(APIModel):
    participant_id: str
    attempt_key: str = "initial"
    answers: dict[str, Any]
    finalize: bool = False


class RevisionCreate(APIModel):
    answers: dict[str, Any]
    correction_reason: str = Field(min_length=1, max_length=2000)
    expected_lock_version: int = Field(ge=1)
    finalize: bool = False


class ValidationIssueView(APIModel):
    item_code: str | None
    error_code: str
    safe_params: dict[str, Any]


class RevisionView(APIModel):
    id: str
    response_id: str
    revision_number: int
    status: str
    answer_payload_hash: str
    validation_summary: dict[str, Any]
    validation_issues: list[ValidationIssueView] = Field(default_factory=list)


class ResponseView(APIModel):
    id: str
    research_id: str
    participant_id: str
    attempt_key: str
    status: str
    lock_version: int
    current_revision_id: str | None


class CalculationRequest(APIModel):
    response_revision_id: str
    idempotency_key: str = Field(min_length=1, max_length=200)


class ScaleResultView(APIModel):
    scale_code: str
    validity_status: str
    reason_codes: list[str]
    answered_count: int
    missing_count: int
    aggregate_score_unrounded: str | None
    score_unrounded: str | None
    score_display: str | None
    unit_code: str
    norm_band_code: str | None
    interpretation_code: str | None
    interpretation_snapshot_i18n: dict[str, str] | None
    disclosure_level_applied: str


class ResultView(APIModel):
    id: str
    research_id: str
    participant_id: str
    response_revision_id: str
    status: str
    disclaimer_i18n: dict[str, str]
    calculated_at: datetime
    result_hash: str
    scales: list[ScaleResultView]
    trace: list[dict[str, Any]]


class CSVPreviewRequest(APIModel):
    csv_text: str

    @field_validator("csv_text")
    @classmethod
    def csv_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CSV content is empty")
        return value


class ImportPreviewView(APIModel):
    import_id: str
    status: str
    preview_hash: str
    summary: dict[str, int]
    errors: list[dict[str, Any]]


class ImportConfirmRequest(APIModel):
    preview_hash: str


class ImportConfirmView(APIModel):
    import_id: str
    status: str
    summary: dict[str, int]
