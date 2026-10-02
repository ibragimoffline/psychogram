from __future__ import annotations

import base64
import os
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.core.config import Settings
from src.core.db import Database
from src.main import create_app
from src.models.domain import Base

# Point at a disposable PostgreSQL database to run the API suite against it; every
# test starts from an empty schema there. The default stays an in-memory SQLite.
TEST_DATABASE_URL = os.environ.get("PSYCHOGRAM_TEST_DATABASE_URL", "sqlite://")

SYNTH_BALANCE_DEMO = {
    "methodology_code": "synth_balance_demo",
    "version_code": "1.0.0",
    "items": [
        {
            "item_code": "q1",
            "item_type": "integer",
            "required": False,
            "value_constraints": {"min": 0, "max": 3, "step": 1},
            "score_mapping": {"mode": "identity"},
            "reverse_scoring": {"mode": "none"},
        },
        {
            "item_code": "q2",
            "item_type": "integer",
            "required": False,
            "value_constraints": {"min": 0, "max": 3, "step": 1},
            "score_mapping": {"mode": "identity"},
            "reverse_scoring": {"mode": "range", "min_score": "0", "max_score": "3"},
        },
        {
            "item_code": "q3",
            "item_type": "integer",
            "required": False,
            "value_constraints": {"min": 0, "max": 3, "step": 1},
            "score_mapping": {"mode": "identity"},
            "reverse_scoring": {"mode": "none"},
        },
        {
            "item_code": "q4",
            "item_type": "integer",
            "required": False,
            "value_constraints": {"min": 0, "max": 3, "step": 1},
            "score_mapping": {"mode": "identity"},
            "reverse_scoring": {"mode": "range", "min_score": "0", "max_score": "3"},
        },
    ],
    "scales": [
        {
            "scale_code": "total",
            "scale_kind": "total",
            "unit_code": "demo_0_10",
            "theoretical_min": "0",
            "theoretical_max": "10",
            "display_decimals": 2,
            "aggregation": {
                "op": "sum_prorated",
                "min_answered": 3,
                "max_missing": 1,
                "target_item_count": 4,
            },
            "transform_expr": {
                "op": "mul",
                "args": [
                    {
                        "op": "div",
                        "left": {"op": "ref", "kind": "aggregate", "code": "total"},
                        "right": {"op": "const", "value": "12"},
                    },
                    {"op": "const", "value": "10"},
                ],
            },
        }
    ],
    "norm": {
        "norm_code": "synthetic_default",
        "norm_kind": "threshold_bands",
        "source_reference": "SYNTHETIC_TEST_ONLY",
        "bands": [
            {
                "band_code": "demo_lower",
                "lower_bound": "0",
                "lower_inclusive": True,
                "upper_bound": "3.333333",
                "upper_inclusive": False,
            },
            {
                "band_code": "demo_middle",
                "lower_bound": "3.333333",
                "lower_inclusive": True,
                "upper_bound": "6.666667",
                "upper_inclusive": False,
            },
            {
                "band_code": "demo_upper",
                "lower_bound": "6.666667",
                "lower_inclusive": True,
                "upper_bound": "10",
                "upper_inclusive": True,
            },
        ],
    },
    "interpretations": [
        {
            "rule_code": "lower_rule",
            "priority": 1,
            "when": {
                "op": "eq",
                "left": {"op": "ref", "kind": "norm_band_code", "code": "total"},
                "right": {"op": "const", "value": "demo_lower"},
            },
            "interpretation_code": "demo_lower_text",
            "text_i18n": {"uz-Latn": "Faqat sintetik pastki demo diapazoni."},
        },
        {
            "rule_code": "middle_rule",
            "priority": 2,
            "when": {
                "op": "eq",
                "left": {"op": "ref", "kind": "norm_band_code", "code": "total"},
                "right": {"op": "const", "value": "demo_middle"},
            },
            "interpretation_code": "demo_middle_text",
            "text_i18n": {"uz-Latn": "Faqat sintetik o'rta demo diapazoni."},
        },
        {
            "rule_code": "upper_rule",
            "priority": 3,
            "when": {
                "op": "eq",
                "left": {"op": "ref", "kind": "norm_band_code", "code": "total"},
                "right": {"op": "const", "value": "demo_upper"},
            },
            "interpretation_code": "demo_upper_text",
            "text_i18n": {"uz-Latn": "Faqat sintetik yuqori demo diapazoni."},
        },
    ],
}

TEST_BOOTSTRAP_TOKEN = "test-bootstrap-token-that-is-long-enough"


@pytest.fixture
def client():
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        auto_create_schema=True,
        jwt_secret="test-secret-that-is-longer-than-thirty-two-characters",
        bootstrap_enabled=True,
        bootstrap_token=TEST_BOOTSTRAP_TOKEN,
        registration_enabled=True,
        csv_import_enabled=True,
        pii_encryption_key=base64.b64encode(b"k" * 32).decode("ascii"),
        cors_origins="http://testserver",
    )
    database = Database(settings)
    Base.metadata.drop_all(database.engine)
    with TestClient(create_app(settings, database)) as value:
        yield value
    database.engine.dispose()


def bearer(token: str, organization_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if organization_id:
        headers["X-Organization-ID"] = organization_id
    return headers


@pytest.fixture
def prepared(client: TestClient):
    admin_token = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "platform@example.com",
            "full_name": "Platform Admin",
            "password": "A-very-safe-admin-password",
            "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
        },
    ).json()["access_token"]
    owner_token = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "full_name": "Owner",
            "password": "A-very-safe-owner-password",
            "organization_name": "Demo Research",
            "organization_code": "demo_research",
            "org_type": "research_center",
            "region": "GLOBAL",
        },
    ).json()["access_token"]
    organization_id = client.get("/api/v1/auth/me", headers=bearer(owner_token)).json()[
        "memberships"
    ][0]["organization_id"]
    methodology = client.post(
        "/api/v1/methodologies",
        headers=bearer(admin_token),
        json={
            "methodology_code": "synth_balance_demo",
            "canonical_name": "Synthetic Balance Demo",
            "purpose_summary": "Automated test fixture only",
            "owner_name": "Synthetic",
            "source_reference": "SYNTHETIC_TEST_ONLY",
        },
    ).json()
    version = client.post(
        f"/api/v1/methodologies/{methodology['id']}/versions",
        headers=bearer(admin_token),
        json={
            "version_code": "1.0.0",
            "default_locale": "uz-Latn",
            "supported_locales": ["uz-Latn"],
            "target_population": {"adults_only": True, "min_age": 18},
            "estimated_minutes": 5,
            "disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "snapshot": SYNTH_BALANCE_DEMO,
        },
    ).json()
    licence = client.post(
        f"/api/v1/methodology-versions/{version['id']}/licences",
        headers=bearer(admin_token),
        json={
            "status": "verified",
            "copyright_status": "public_domain",
            "rights_holder": "Synthetic",
            "evidence_reference": "SYNTHETIC_TEST_ONLY",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "full",
            "allow_item_display": True,
            "allow_item_export": True,
            "allow_trace_item_values": True,
            "valid_from": str(date.today() - timedelta(days=1)),
            "valid_until": str(date.today() + timedelta(days=365)),
            "required_disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "restrictions_i18n": {"uz-Latn": "Faqat sintetik test."},
            "change_reason": "Initial synthetic test fixture",
        },
    ).json()
    publish = client.post(
        f"/api/v1/methodology-versions/{version['id']}/publish",
        headers=bearer(admin_token),
        json={"reason": "Synthetic tests"},
    )
    assert publish.status_code == 200, publish.text
    policy = client.post(
        "/api/v1/retention-policies",
        headers=bearer(owner_token, organization_id),
        json={"code": "test_365", "retention_days": 365},
    ).json()
    research = client.post(
        "/api/v1/researches",
        headers=bearer(owner_token, organization_id),
        json={
            "name": "Synthetic only",
            "purpose": "Automated tests",
            "methodology_version_id": version["id"],
            "pii_mode": "anonymous",
            "consent_reference": "CONSENT-TEST",
            "consent_version": "1",
            "retention_policy_id": policy["id"],
            "norm_selection": {},
            "use_type": "research",
        },
    ).json()
    activation = client.post(
        f"/api/v1/researches/{research['id']}/activate",
        headers=bearer(owner_token, organization_id),
    )
    assert activation.status_code == 200, activation.text
    participant = client.post(
        f"/api/v1/researches/{research['id']}/participants",
        headers=bearer(owner_token, organization_id),
        json={"external_code": "P-001"},
    ).json()
    consent = client.post(
        f"/api/v1/participants/{participant['id']}/consents",
        headers=bearer(owner_token, organization_id),
        json={
            "status": "granted",
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    assert consent.status_code == 201, consent.text
    return {
        "client": client,
        "admin_token": admin_token,
        "owner_token": owner_token,
        "organization_id": organization_id,
        "methodology": methodology,
        "version": version,
        "licence": licence,
        "policy": policy,
        "research": research,
        "participant": participant,
    }
