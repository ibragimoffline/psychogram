from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PSYCHOGRAM_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Psychogram API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./psychogram.db"
    auto_create_schema: bool = False
    jwt_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(48))
    )
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    bootstrap_enabled: bool = False
    bootstrap_token: SecretStr | None = None
    pii_encryption_key: SecretStr | None = None
    pii_key_version: str = "v1"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    max_csv_bytes: int = 1_000_000
    max_csv_rows: int = 10_000
    max_request_body_bytes: int = 3_100_000

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: str) -> str:
        if "*" in {part.strip() for part in value.split(",")}:
            raise ValueError("Wildcard CORS is not allowed")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.bootstrap_enabled:
            if self.bootstrap_token is None:
                raise ValueError(
                    "BOOTSTRAP_TOKEN is required when bootstrap is enabled"
                )
            if len(self.bootstrap_token.get_secret_value()) < 32:
                raise ValueError(
                    "BOOTSTRAP_TOKEN must be at least 32 characters when enabled"
                )
        if self.environment.lower() == "production":
            if "jwt_secret" not in self.model_fields_set:
                raise ValueError(
                    "JWT_SECRET must be explicitly configured in production"
                )
            if len(self.jwt_secret.get_secret_value()) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters in production"
                )
            if self.pii_encryption_key is not None:
                self._validate_pii_key(self.pii_encryption_key)
        if self.max_request_body_bytes <= self.max_csv_bytes:
            raise ValueError(
                "MAX_REQUEST_BODY_BYTES must exceed MAX_CSV_BYTES for JSON framing"
            )
        return self

    @field_validator("pii_encryption_key")
    @classmethod
    def validate_pii_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            cls._validate_pii_key(value)
        return value

    @staticmethod
    def _validate_pii_key(value: SecretStr) -> None:
        import base64
        import binascii

        try:
            decoded = base64.b64decode(
                value.get_secret_value(), altchars=b"-_", validate=True
            )
        except (ValueError, binascii.Error) as exc:
            raise ValueError("PII_ENCRYPTION_KEY must be valid base64") from exc
        if len(decoded) != 32:
            raise ValueError("PII_ENCRYPTION_KEY must decode to exactly 32 bytes")

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
