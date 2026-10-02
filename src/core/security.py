from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from src.core.config import Settings
from src.core.errors import DomainError

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise DomainError(
            "PASSWORD_TOO_WEAK", "Password must contain at least 12 characters"
        )
    return _password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _password_hash.verify(password, encoded)
    except Exception:
        return False


def create_access_token(user_id: UUID | str, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": expires, "type": "access"},
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, settings.access_token_minutes * 60


def decode_access_token(token: str, settings: Settings) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise DomainError(
            "AUTH_TOKEN_INVALID", "Access token is invalid or expired", 401
        ) from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise DomainError("AUTH_TOKEN_INVALID", "Access token is invalid", 401)
    return str(payload["sub"])
