from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import current_user, get_db, get_runtime_settings
from src.core.config import Settings
from src.core.security import create_access_token
from src.models.domain import Membership, Organization, User
from src.schemas.api import (
    BootstrapRequest,
    LoginRequest,
    MeResponse,
    MembershipView,
    RegisterRequest,
    TokenResponse,
)
from src.services.domain import authenticate, bootstrap_user, register_owner

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _token(user: User, settings: Settings) -> TokenResponse:
    value, expires = create_access_token(user.id, settings)
    return TokenResponse(access_token=value, expires_in=expires)


@router.post("/bootstrap", response_model=TokenResponse, status_code=201)
def bootstrap(
    payload: BootstrapRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
):
    token = (
        settings.bootstrap_token.get_secret_value() if settings.bootstrap_token else ""
    )
    user = bootstrap_user(db, payload, token, enabled=settings.bootstrap_enabled)
    db.commit()
    return _token(user, settings)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
):
    user, _organization = register_owner(db, payload)
    db.commit()
    return _token(user, settings)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
):
    user = authenticate(db, str(payload.email), payload.password)
    db.commit()
    return _token(user, settings)


@router.get("/me", response_model=MeResponse)
def me(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.tenant_id)
        .where(
            Membership.user_id == user.id,
            Membership.active.is_(True),
            Organization.active.is_(True),
        )
    ).all()
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_platform_admin=user.is_platform_admin,
        memberships=[
            MembershipView(
                organization_id=organization.id,
                organization_name=organization.name,
                role=membership.role,
                can_view_pii=membership.can_view_pii,
            )
            for membership, organization in memberships
        ],
    )
