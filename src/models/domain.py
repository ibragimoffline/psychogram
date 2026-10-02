from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    event,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm.state import InstanceState


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)


class CreatedMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Organization(Base, IdMixin, CreatedMixin):
    __tablename__ = "organizations"
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="research_center"
    )
    region: Mapped[str] = mapped_column(String(16), nullable=False, default="GLOBAL")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base, IdMixin, CreatedMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Membership(Base, IdMixin, CreatedMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
        CheckConstraint(
            "role in ('owner','admin','researcher','operator','auditor')",
            name="ck_membership_role",
        ),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    can_view_pii: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Methodology(Base, IdMixin, CreatedMixin):
    __tablename__ = "methodologies"
    methodology_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose_summary: Mapped[str] = mapped_column(Text, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    catalog_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class MethodologyVersion(Base, IdMixin, CreatedMixin):
    __tablename__ = "methodology_versions"
    __table_args__ = (
        UniqueConstraint(
            "methodology_id", "version_code", name="uq_methodology_version"
        ),
        CheckConstraint(
            "lifecycle_status in "
            "('draft','in_review','published','deprecated','withdrawn')",
            name="ck_methodology_version_status",
        ),
    )
    methodology_id: Mapped[str] = mapped_column(
        ForeignKey("methodologies.id"), nullable=False
    )
    version_code: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(40), default="methodology-contract/1", nullable=False
    )
    default_locale: Mapped[str] = mapped_column(String(32), nullable=False)
    supported_locales: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_population: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )
    content_hash: Mapped[str | None] = mapped_column(String(72), nullable=True)
    engine_contract_version: Mapped[str] = mapped_column(
        String(32), default="scoring/1", nullable=False
    )
    disclaimer_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    template_id: Mapped[str] = mapped_column(String(80), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    supersedes_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("methodology_versions.id")
    )


class Scale(Base, IdMixin):
    __tablename__ = "scales"
    __table_args__ = (
        UniqueConstraint("methodology_version_id", "scale_code", name="uq_scale_code"),
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    scale_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scale_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    label_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    unit_code: Mapped[str] = mapped_column(String(64), nullable=False)
    theoretical_min: Mapped[str] = mapped_column(String(40), nullable=False)
    theoretical_max: Mapped[str] = mapped_column(String(40), nullable=False)
    display_decimals: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    aggregation: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    transform_expr: Mapped[dict | None] = mapped_column(JSON)
    validity_rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Item(Base, IdMixin):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("methodology_version_id", "item_code", name="uq_item_code"),
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    value_constraints: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    score_mapping: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reverse_scoring: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    item_transform_expr: Mapped[dict | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ScaleItemLink(Base, IdMixin):
    __tablename__ = "scale_item_links"
    __table_args__ = (UniqueConstraint("scale_id", "item_id", name="uq_scale_item"),)
    scale_id: Mapped[str] = mapped_column(ForeignKey("scales.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False)
    weight: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ResponseOption(Base, IdMixin):
    __tablename__ = "response_options"
    __table_args__ = (
        UniqueConstraint("item_id", "option_code", name="uq_item_option"),
    )
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False)
    option_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)
    score_value: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class NormSet(Base, IdMixin):
    __tablename__ = "norm_sets"
    __table_args__ = (UniqueConstraint("scale_id", "norm_code", name="uq_scale_norm"),)
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    scale_id: Mapped[str] = mapped_column(ForeignKey("scales.id"), nullable=False)
    norm_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    norm_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    population_descriptor: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    selection_constraints: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    source_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lookup_mode: Mapped[str] = mapped_column(
        String(16), default="exact", nullable=False
    )


class NormBand(Base, IdMixin):
    __tablename__ = "norm_bands"
    __table_args__ = (
        UniqueConstraint("norm_set_id", "band_code", name="uq_norm_band"),
    )
    norm_set_id: Mapped[str] = mapped_column(ForeignKey("norm_sets.id"), nullable=False)
    band_code: Mapped[str] = mapped_column(String(64), nullable=False)
    lower_bound: Mapped[str | None] = mapped_column(String(40))
    lower_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    upper_bound: Mapped[str | None] = mapped_column(String(40))
    upper_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(40))
    label_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class InterpretationRule(Base, IdMixin):
    __tablename__ = "interpretation_rules"
    __table_args__ = (
        UniqueConstraint("scale_id", "rule_code", name="uq_interpretation_rule"),
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    scale_id: Mapped[str] = mapped_column(ForeignKey("scales.id"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    when_expr: Mapped[dict] = mapped_column(JSON, nullable=False)
    interpretation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    text_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    disclaimer_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LicenceRevision(Base, IdMixin, CreatedMixin):
    __tablename__ = "licence_revisions"
    __table_args__ = (
        UniqueConstraint(
            "methodology_version_id", "licence_revision", name="uq_licence_revision"
        ),
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    licence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    copyright_status: Mapped[str] = mapped_column(String(32), nullable=False)
    rights_holder: Mapped[str] = mapped_column(String(300), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    allowed_use_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    allowed_org_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    allowed_regions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    content_disclosure_level: Mapped[str] = mapped_column(String(24), nullable=False)
    allow_item_display: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_item_export: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_trace_item_values: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    required_disclaimer_i18n: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    restrictions_i18n: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    verified_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)


class RetentionPolicy(Base, IdMixin, CreatedMixin):
    __tablename__ = "retention_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_retention_tenant_code"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Research(Base, IdMixin, CreatedMixin):
    __tablename__ = "researches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_research_tenant_id"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    pii_mode: Mapped[str] = mapped_column(
        String(24), default="pseudonymous", nullable=False
    )
    consent_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_policy_id: Mapped[str] = mapped_column(
        ForeignKey("retention_policies.id"), nullable=False
    )
    responsible_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    use_type: Mapped[str] = mapped_column(
        String(24), default="research", nullable=False
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ResearchMethodologyPin(Base, IdMixin, CreatedMixin):
    __tablename__ = "research_methodology_pins"
    __table_args__ = (
        UniqueConstraint("tenant_id", "research_id", name="uq_research_pin"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    methodology_content_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    norm_selection: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    pinned_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class Participant(Base, IdMixin, CreatedMixin):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "research_id", "external_code", name="uq_participant_code"
        ),
        UniqueConstraint("tenant_id", "research_id", "id", name="uq_participant_scope"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False, index=True
    )
    external_code: Mapped[str] = mapped_column(String(120), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(24), default="active", nullable=False
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ParticipantPII(Base, IdMixin, CreatedMixin):
    __tablename__ = "participant_pii"
    __table_args__ = (
        UniqueConstraint("tenant_id", "participant_id", name="uq_participant_pii"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(String(32), nullable=False)
    algorithm: Mapped[str] = mapped_column(
        String(32), default="AES-256-GCM", nullable=False
    )
    key_version: Mapped[str] = mapped_column(String(64), nullable=False)
    field_names: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ConsentRecord(Base, IdMixin, CreatedMixin):
    __tablename__ = "consent_records"
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    obtained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    basis: Mapped[str | None] = mapped_column(Text)
    record_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Response(Base, IdMixin, CreatedMixin):
    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "research_id",
            "participant_id",
            "attempt_key",
            name="uq_response_attempt",
        ),
        UniqueConstraint("tenant_id", "research_id", "id", name="uq_response_scope"),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False, index=True
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    attempt_key: Mapped[str] = mapped_column(
        String(64), default="initial", nullable=False
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class ResponseRevision(Base, IdMixin, CreatedMixin):
    __tablename__ = "response_revisions"
    __table_args__ = (
        UniqueConstraint(
            "response_id", "revision_number", name="uq_response_revision_number"
        ),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    answer_payload_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    validation_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(36))
    correction_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ResponseValidationIssue(Base, IdMixin):
    __tablename__ = "response_validation_issues"
    response_revision_id: Mapped[str] = mapped_column(
        ForeignKey("response_revisions.id"), nullable=False
    )
    item_code: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class CalculationRun(Base, IdMixin, CreatedMixin):
    __tablename__ = "calculation_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "computation_key", name="uq_calculation_computation"
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_calculation_idempotency"
        ),
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    response_revision_id: Mapped[str] = mapped_column(
        ForeignKey("response_revisions.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    computation_key: Mapped[str] = mapped_column(String(72), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_interpreter_version: Mapped[str] = mapped_column(String(32), nullable=False)
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    methodology_content_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    licence_id: Mapped[str] = mapped_column(
        ForeignKey("licence_revisions.id"), nullable=False
    )
    licence_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    initiated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    diagnostic_ref: Mapped[str | None] = mapped_column(String(64))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Result(Base, IdMixin):
    __tablename__ = "results"
    calculation_run_id: Mapped[str] = mapped_column(
        ForeignKey("calculation_runs.id"), unique=True, nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id"), nullable=False)
    response_revision_id: Mapped[str] = mapped_column(
        ForeignKey("response_revisions.id"), nullable=False
    )
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    methodology_content_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    status: Mapped[str] = mapped_column(String(48), nullable=False)
    disclaimer_i18n_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    calculated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    retention_classification: Mapped[str] = mapped_column(
        String(64), default="research", nullable=False
    )


class ScaleResult(Base, IdMixin):
    __tablename__ = "scale_results"
    __table_args__ = (
        UniqueConstraint("result_id", "scale_code", name="uq_result_scale"),
    )
    result_id: Mapped[str] = mapped_column(ForeignKey("results.id"), nullable=False)
    scale_id: Mapped[str | None] = mapped_column(ForeignKey("scales.id"))
    scale_code: Mapped[str] = mapped_column(String(64), nullable=False)
    validity_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    answered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregate_score_unrounded: Mapped[str | None] = mapped_column(String(80))
    score_unrounded: Mapped[str | None] = mapped_column(String(80))
    score_display: Mapped[str | None] = mapped_column(String(80))
    unit_code: Mapped[str] = mapped_column(String(64), nullable=False)
    norm_set_id: Mapped[str | None] = mapped_column(ForeignKey("norm_sets.id"))
    norm_band_code: Mapped[str | None] = mapped_column(String(64))
    normalized_value: Mapped[str | None] = mapped_column(String(80))
    interpretation_rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("interpretation_rules.id")
    )
    interpretation_code: Mapped[str | None] = mapped_column(String(64))
    interpretation_snapshot_i18n: Mapped[dict | None] = mapped_column(JSON)
    disclosure_level_applied: Mapped[str] = mapped_column(String(24), nullable=False)


class ExplainabilityTrace(Base, IdMixin):
    __tablename__ = "explainability_traces"
    calculation_run_id: Mapped[str] = mapped_column(
        ForeignKey("calculation_runs.id"), unique=True, nullable=False
    )
    result_id: Mapped[str] = mapped_column(
        ForeignKey("results.id"), unique=True, nullable=False
    )
    trace_schema_version: Mapped[str] = mapped_column(
        String(32), default="explainability/1", nullable=False
    )
    disclosure_level_applied: Mapped[str] = mapped_column(String(24), nullable=False)
    methodology_content_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    response_revision_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    trace_hash: Mapped[str] = mapped_column(String(72), nullable=False)


class TraceStep(Base, IdMixin):
    __tablename__ = "trace_steps"
    __table_args__ = (
        UniqueConstraint("trace_id", "sequence", name="uq_trace_sequence"),
    )
    trace_id: Mapped[str] = mapped_column(
        ForeignKey("explainability_traces.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_ref: Mapped[dict | None] = mapped_column(JSON)
    rule_ref: Mapped[str | None] = mapped_column(String(200))
    inputs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    outputs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    message_key: Mapped[str] = mapped_column(String(160), nullable=False)
    redactions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class ImportJob(Base, IdMixin, CreatedMixin):
    __tablename__ = "import_jobs"
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    preview_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    staged_rows: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ImportRow(Base, IdMixin):
    __tablename__ = "import_rows"
    import_job_id: Mapped[str] = mapped_column(
        ForeignKey("import_jobs.id"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    participant_id: Mapped[str | None] = mapped_column(ForeignKey("participants.id"))
    response_id: Mapped[str | None] = mapped_column(ForeignKey("responses.id"))


class ImportIssue(Base, IdMixin):
    __tablename__ = "import_issues"
    import_job_id: Mapped[str] = mapped_column(
        ForeignKey("import_jobs.id"), nullable=False
    )
    row_number: Mapped[int | None] = mapped_column(Integer)
    column_name: Mapped[str | None] = mapped_column(String(160))
    item_code: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ColumnMapping(Base, IdMixin, CreatedMixin):
    __tablename__ = "column_mappings"
    methodology_version_id: Mapped[str] = mapped_column(
        ForeignKey("methodology_versions.id"), nullable=False
    )
    template_id: Mapped[str] = mapped_column(String(80), nullable=False)
    source_headers_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    columns: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    research_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default=new_id
    )
    safe_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LegalHold(Base, IdMixin, CreatedMixin):
    __tablename__ = "legal_holds"
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    research_id: Mapped[str] = mapped_column(
        ForeignKey("researches.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)


@event.listens_for(Session, "before_flush")
def enforce_immutable_records(session: Session, _flush_context, _instances) -> None:
    """ORM-level safety net for immutable domain snapshots.

    PostgreSQL deployments should additionally restrict application roles from direct
    table updates; this hook protects every normal SQLAlchemy write path.
    """
    immutable_always = (Result, ScaleResult, ExplainabilityTrace, TraceStep, AuditEvent)
    for obj in session.dirty:
        state = cast(InstanceState[Any], inspect(obj))
        if isinstance(obj, immutable_always) and state.persistent:
            raise ValueError(f"{type(obj).__name__} is immutable")
        if isinstance(obj, MethodologyVersion):
            old_status = state.attrs.lifecycle_status.history.deleted
            if old_status and old_status[0] in {"published", "deprecated", "withdrawn"}:
                raise ValueError("Published methodology version is immutable")
        if isinstance(obj, ResponseRevision):
            old_status = state.attrs.status.history.deleted
            if old_status and old_status[0] in {"validated", "superseded", "withdrawn"}:
                raise ValueError("Validated response revision is immutable")
        if isinstance(obj, ResearchMethodologyPin) and inspect(obj).persistent:
            research = session.get(Research, obj.research_id)
            if research and research.status == "active":
                raise ValueError("Active research methodology pin is immutable")
    for obj in session.deleted:
        if isinstance(
            obj, immutable_always + (MethodologyVersion, ResponseRevision, AuditEvent)
        ):
            raise ValueError(
                f"{type(obj).__name__} cannot be deleted through the "
                "application session"
            )
        if isinstance(obj, ResearchMethodologyPin):
            research = session.get(Research, obj.research_id)
            if research and research.status == "active":
                raise ValueError("Active research methodology pin cannot be deleted")
