from __future__ import annotations

import base64
import json
import os
from datetime import UTC, datetime

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.core.errors import DomainError
from src.models.domain import (
    LegalHold,
    Participant,
    ParticipantPII,
    Research,
)
from src.services.audit import audit

ALGORITHM = "AES-256-GCM"


def _key(settings: Settings) -> bytes:
    if settings.pii_encryption_key is None:
        raise DomainError(
            "PII_KEY_NOT_CONFIGURED",
            "PII encryption is unavailable in this deployment",
            503,
        )
    return base64.b64decode(
        settings.pii_encryption_key.get_secret_value(),
        altchars=b"-_",
        validate=True,
    )


def _aad(participant: Participant, key_version: str) -> bytes:
    return (
        f"psychogram-pii|{participant.tenant_id}|{participant.research_id}|"
        f"{participant.id}|{key_version}"
    ).encode("utf-8")


def upsert_pii(
    db: Session,
    *,
    research: Research,
    participant: Participant,
    fields: dict[str, str],
    actor_id: str,
    settings: Settings,
) -> ParticipantPII:
    _require_identified_scope(research, participant)
    key = _key(settings)
    nonce = os.urandom(12)
    plaintext = json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(
        nonce, plaintext, _aad(participant, settings.pii_key_version)
    )
    record = db.scalar(
        select(ParticipantPII).where(
            ParticipantPII.tenant_id == research.tenant_id,
            ParticipantPII.participant_id == participant.id,
        )
    )
    action = "pii.update" if record else "pii.create"
    if record is None:
        record = ParticipantPII(
            tenant_id=research.tenant_id,
            participant_id=participant.id,
            encrypted_payload="",
            nonce="",
            key_version=settings.pii_key_version,
            updated_by=actor_id,
        )
        db.add(record)
    record.encrypted_payload = base64.b64encode(ciphertext).decode("ascii")
    record.nonce = base64.b64encode(nonce).decode("ascii")
    record.algorithm = ALGORITHM
    record.key_version = settings.pii_key_version
    record.field_names = sorted(fields)
    record.updated_at = datetime.now(UTC)
    record.updated_by = actor_id
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action=action,
        object_type="participant_pii",
        object_id=record.id,
        safe_metadata={"field_names": sorted(fields)},
    )
    return record


def view_pii(
    db: Session,
    *,
    research: Research,
    participant: Participant,
    actor_id: str,
    settings: Settings,
) -> tuple[ParticipantPII, dict[str, str]]:
    _require_identified_scope(research, participant)
    record = db.scalar(
        select(ParticipantPII).where(
            ParticipantPII.tenant_id == research.tenant_id,
            ParticipantPII.participant_id == participant.id,
        )
    )
    if record is None:
        raise DomainError("PII_NOT_FOUND", "Participant PII was not found", 404)
    if record.key_version != settings.pii_key_version:
        raise DomainError(
            "PII_KEY_VERSION_UNAVAILABLE",
            "The key version required for this PII record is unavailable",
            503,
        )
    try:
        plaintext = AESGCM(_key(settings)).decrypt(
            base64.b64decode(record.nonce, validate=True),
            base64.b64decode(record.encrypted_payload, validate=True),
            _aad(participant, record.key_version),
        )
        fields = json.loads(plaintext.decode("utf-8"))
    except (InvalidTag, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError(
            "PII_DECRYPTION_FAILED",
            "Participant PII could not be decrypted with the configured key",
            503,
        ) from exc
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="pii.view",
        object_type="participant_pii",
        object_id=record.id,
        safe_metadata={"field_names": list(record.field_names)},
    )
    return record, fields


def delete_pii(
    db: Session,
    *,
    research: Research,
    participant: Participant,
    actor_id: str,
) -> None:
    _require_identified_scope(research, participant)
    hold = db.scalar(
        select(LegalHold).where(
            LegalHold.tenant_id == research.tenant_id,
            LegalHold.research_id == research.id,
            LegalHold.active.is_(True),
        )
    )
    if hold:
        raise DomainError(
            "PII_DELETE_LEGAL_HOLD",
            "Participant PII cannot be deleted while a legal hold is active",
            409,
        )
    record = db.scalar(
        select(ParticipantPII).where(
            ParticipantPII.tenant_id == research.tenant_id,
            ParticipantPII.participant_id == participant.id,
        )
    )
    if record is None:
        raise DomainError("PII_NOT_FOUND", "Participant PII was not found", 404)
    field_names = list(record.field_names)
    record_id = record.id
    db.delete(record)
    audit(
        db,
        actor_id=actor_id,
        tenant_id=research.tenant_id,
        research_id=research.id,
        action="pii.delete",
        object_type="participant_pii",
        object_id=record_id,
        safe_metadata={"field_names": field_names},
    )


def _require_identified_scope(research: Research, participant: Participant) -> None:
    if research.pii_mode != "identified":
        raise DomainError(
            "PII_MODE_NOT_IDENTIFIED",
            "Direct PII is only available for identified research",
            409,
        )
    if (
        participant.tenant_id != research.tenant_id
        or participant.research_id != research.id
    ):
        raise DomainError(
            "TENANT_ACCESS_DENIED",
            "Participant is outside the active research scope",
            404,
        )
