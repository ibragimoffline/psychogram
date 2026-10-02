from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from src.schemas.api import APIModel, ScaleResultView, ValidationIssueView


class RetentionPolicyView(APIModel):
    id: str
    code: str
    retention_days: int
    active: bool
    created_at: datetime


class LicenceDetailView(APIModel):
    id: str
    methodology_version_id: str
    licence_revision: int
    status: str
    copyright_status: str
    rights_holder: str
    evidence_reference: str | None = None
    allowed_use_types: list[str]
    allowed_org_types: list[str]
    allowed_regions: list[str]
    content_disclosure_level: str
    allow_item_display: bool
    allow_item_export: bool
    allow_trace_item_values: bool
    valid_from: date
    valid_until: date | None
    restrictions_i18n: dict[str, str]
    change_reason: str | None = None
    current: bool = False
    eligible: bool = False


class MethodologyVersionDetailView(APIModel):
    id: str
    methodology_id: str
    methodology_code: str
    methodology_name: str
    version_code: str
    lifecycle_status: str
    schema_version: str
    default_locale: str
    supported_locales: list[str]
    target_population: dict[str, Any]
    estimated_minutes: int
    content_hash: str | None
    engine_contract_version: str
    disclaimer_i18n: dict[str, str]
    template_id: str
    published_at: datetime | None
    snapshot: dict[str, Any] | None
    licence: LicenceDetailView | None
    eligible: bool


class MethodologyDetailView(APIModel):
    id: str
    methodology_code: str
    canonical_name: str
    purpose_summary: str
    owner_name: str | None
    source_reference: str | None
    catalog_status: str
    versions: list[MethodologyVersionDetailView]


class ParticipantListItem(APIModel):
    id: str
    research_id: str
    external_code: str
    processing_status: str
    created_at: datetime
    current_consent_status: str | None
    has_pii: bool


class ParticipantPage(APIModel):
    items: list[ParticipantListItem]
    total: int
    offset: int
    limit: int


class ParticipantDetailView(ParticipantListItem):
    created_by: str


class ConsentHistoryItem(APIModel):
    id: str
    participant_id: str
    status: str
    reference: str
    version: str
    obtained_at: datetime
    recorded_by: str
    basis: str | None
    record_version: int
    created_at: datetime


class ConsentHistoryView(APIModel):
    current: ConsentHistoryItem | None
    history: list[ConsentHistoryItem]


class RevisionDetailView(APIModel):
    id: str
    response_id: str
    revision_number: int
    status: str
    answer_payload_hash: str
    validation_summary: dict[str, Any]
    source_type: str
    correction_reason: str | None
    created_at: datetime
    created_by: str
    validated_at: datetime | None
    validated_by: str | None
    answers: dict[str, Any] | None
    is_current: bool
    validation_issues: list[ValidationIssueView]


class ResponseListItem(APIModel):
    id: str
    research_id: str
    participant_id: str
    participant_external_code: str
    attempt_key: str
    status: str
    lock_version: int
    current_revision_id: str | None
    current_revision_number: int | None
    current_revision_status: str | None
    created_at: datetime


class ResponsePage(APIModel):
    items: list[ResponseListItem]
    total: int
    offset: int
    limit: int


class ResponseDetailView(ResponseListItem):
    methodology_version_id: str
    current_revision: RevisionDetailView | None


class RevisionHistoryView(APIModel):
    response_id: str
    current_revision_id: str | None
    revisions: list[RevisionDetailView]


class ResultSummaryView(APIModel):
    id: str
    research_id: str
    participant_id: str
    response_id: str
    response_revision_id: str
    status: str
    calculated_at: datetime
    result_hash: str
    disclaimer_i18n: dict[str, str]
    scales: list[ScaleResultView]


class ResultPage(APIModel):
    items: list[ResultSummaryView]
    total: int
    offset: int
    limit: int


class PIIWrite(APIModel):
    fields: dict[str, str] = Field(min_length=1, max_length=12)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = {
            "full_name",
            "email",
            "phone",
            "address",
            "national_id",
            "date_of_birth",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unsupported PII fields: {', '.join(sorted(unknown))}")
        cleaned: dict[str, str] = {}
        for key, item in value.items():
            normalized = item.strip()
            if not normalized or len(normalized) > 1000:
                raise ValueError(f"PII field '{key}' must contain 1..1000 characters")
            cleaned[key] = normalized
        return cleaned


class PIIView(APIModel):
    participant_id: str
    fields: dict[str, str]
    algorithm: str
    key_version: str
    updated_at: datetime
