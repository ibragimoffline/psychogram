from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.core.errors import DomainError
from src.core.security import decode_access_token
from src.models.domain import Membership, Organization, User

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    db = request.app.state.database.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise DomainError("AUTH_REQUIRED", "Bearer access token is required", 401)
    user_id = decode_access_token(credentials.credentials, settings)
    user = db.get(User, user_id)
    if not user or not user.active:
        raise DomainError(
            "AUTH_REQUIRED", "Authenticated user is inactive or missing", 401
        )
    return user


def platform_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_platform_admin:
        raise DomainError(
            "ROLE_FORBIDDEN", "Platform administrator role is required", 403
        )
    return user


@dataclass
class TenantContext:
    organization: Organization
    membership: Membership


def tenant_context(
    organization_id: Annotated[str, Header(alias="X-Organization-ID")],
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TenantContext:
    membership = db.scalar(
        select(Membership).where(
            Membership.tenant_id == organization_id,
            Membership.user_id == user.id,
            Membership.active.is_(True),
        )
    )
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.active.is_(True),
        )
    )
    if not membership or not organization:
        raise DomainError(
            "TENANT_ACCESS_DENIED", "Active organization membership was not found", 403
        )
    return TenantContext(organization=organization, membership=membership)


def roles(*allowed: str):
    def dependency(
        context: Annotated[TenantContext, Depends(tenant_context)],
    ) -> TenantContext:
        if context.membership.role not in allowed:
            raise DomainError(
                "ROLE_FORBIDDEN", "Organization role does not allow this operation", 403
            )
        return context

    return dependency


def pii_access(
    context: Annotated[TenantContext, Depends(tenant_context)],
) -> TenantContext:
    if context.membership.role not in {"owner", "admin", "researcher"}:
        raise DomainError(
            "PII_ROLE_FORBIDDEN", "Organization role cannot access PII", 403
        )
    if not context.membership.can_view_pii:
        raise DomainError("PII_PERMISSION_REQUIRED", "PII permission is required", 403)
    return context
