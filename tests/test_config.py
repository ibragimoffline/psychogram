from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from src.core.config import Settings


def test_production_requires_explicit_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="explicitly configured"):
        Settings(_env_file=None, environment="production")


def test_production_accepts_strong_explicit_jwt_secret() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret=SecretStr("x" * 32),
    )
    assert settings.environment == "production"


def test_bootstrap_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.bootstrap_enabled is False


def test_enabled_bootstrap_requires_a_strong_token() -> None:
    with pytest.raises(ValidationError, match="required when bootstrap is enabled"):
        Settings(_env_file=None, bootstrap_enabled=True)
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            _env_file=None,
            bootstrap_enabled=True,
            bootstrap_token=SecretStr("too-short"),
        )


def test_production_accepts_explicit_bootstrap_gate_and_token() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret=SecretStr("x" * 32),
        bootstrap_enabled=True,
        bootstrap_token=SecretStr("b" * 32),
    )
    assert settings.bootstrap_enabled is True
