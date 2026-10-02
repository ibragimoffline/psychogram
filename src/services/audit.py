from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.domain import AuditEvent


def audit(
    db: Session,
    *,
    actor_id: str | None,
    action: str,
    object_type: str,
    object_id: str | None = None,
    tenant_id: str | None = None,
    research_id: str | None = None,
    outcome: str = "success",
    reason_code: str | None = None,
    safe_metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        tenant_id=tenant_id,
        research_id=research_id,
        outcome=outcome,
        reason_code=reason_code,
        safe_metadata=safe_metadata or {},
    )
    db.add(event)
    return event
