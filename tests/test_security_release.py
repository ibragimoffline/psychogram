from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from src.core.config import Settings
from src.core.db import Database
from src.main import create_app
from tests.conftest import TEST_BOOTSTRAP_TOKEN, bearer
from tests.test_api import calculate, create_response
from tests.test_ux_backend_gaps import create_identified_context


def test_bootstrap_endpoint_is_disabled_without_explicit_gate() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_create_schema=True,
        jwt_secret="test-secret-that-is-longer-than-thirty-two-characters",
        pii_encryption_key=base64.b64encode(b"k" * 32).decode("ascii"),
        cors_origins="http://testserver",
    )
    with TestClient(create_app(settings, Database(settings))) as client:
        response = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "email": "admin@example.com",
                "full_name": "Admin",
                "password": "A-secure-bootstrap-password",
                "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
            },
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BOOTSTRAP_DISABLED"


def test_auditor_and_operator_cannot_export_results(prepared) -> None:
    response = create_response(prepared)
    result = calculate(
        prepared, response["current_revision_id"], "auditor-export-deny"
    ).json()
    for role in ("auditor", "operator"):
        email = f"{role}-export@example.com"
        password = f"A-secure-{role}-password"
        member = prepared["client"].post(
            "/api/v1/organizations/current/members",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
            json={
                "email": email,
                "full_name": f"Export {role.title()}",
                "password": password,
                "role": role,
                "can_view_pii": False,
            },
        )
        assert member.status_code == 201, member.text
        token = (
            prepared["client"]
            .post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            .json()["access_token"]
        )
        denied = prepared["client"].get(
            f"/api/v1/results/{result['id']}/export?format=json",
            headers=bearer(token, prepared["organization_id"]),
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_security_headers_and_sensitive_no_store(prepared) -> None:
    health = prepared["client"].get("/health")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert health.headers["x-frame-options"] == "DENY"
    cors = prepared["client"].options(
        "/api/v1/researches",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors.headers["access-control-allow-origin"] == "http://testserver"

    response = create_response(prepared)
    result = calculate(prepared, response["current_revision_id"], "security-headers")
    assert result.headers["cache-control"] == "no-store, private"
    assert result.headers["pragma"] == "no-cache"
    assert result.headers["content-security-policy"].startswith("default-src 'none'")
    read = prepared["client"].get(
        f"/api/v1/results/{result.json()['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert read.headers["cache-control"] == "no-store, private"
    exported = prepared["client"].get(
        f"/api/v1/results/{result.json()['id']}/export?format=json",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert exported.headers["cache-control"] == "no-store, private"

    research, participant = create_identified_context(prepared, "headers")
    pii_path = (
        f"/api/v1/researches/{research['id']}/participants/" f"{participant['id']}/pii"
    )
    pii_headers = bearer(prepared["owner_token"], prepared["organization_id"])
    written = prepared["client"].put(
        pii_path,
        headers=pii_headers,
        json={"fields": {"full_name": "Sensitive Header Test"}},
    )
    assert written.headers["cache-control"] == "no-store, private"
    viewed = prepared["client"].get(pii_path, headers=pii_headers)
    assert viewed.headers["cache-control"] == "no-store, private"
    deleted = prepared["client"].delete(pii_path, headers=pii_headers)
    assert deleted.status_code == 204
    assert deleted.headers["cache-control"] == "no-store, private"


def test_import_preview_rejects_declared_non_utf8_and_oversize(prepared) -> None:
    path = f"/api/v1/researches/{prepared['research']['id']}/imports/preview"
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    headers["Content-Type"] = "application/json; charset=windows-1251"
    encoding = prepared["client"].post(path, headers=headers, content=b"{}")
    assert encoding.status_code == 415
    assert encoding.json()["error"]["code"] == "ENCODING_INVALID"

    headers["Content-Type"] = "application/json"
    headers["Content-Length"] = str(
        prepared["client"].app.state.settings.max_request_body_bytes + 1
    )
    oversized = prepared["client"].post(path, headers=headers, content=b"{}")
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "REQUEST_BODY_TOO_LARGE"


def test_version_detail_uses_validated_use_type_and_pinned_research(prepared) -> None:
    licence = prepared["client"].post(
        f"/api/v1/methodology-versions/{prepared['version']['id']}/licences",
        headers=bearer(prepared["admin_token"]),
        json={
            "status": "verified",
            "copyright_status": "permission_granted",
            "rights_holder": "Synthetic Test",
            "evidence_reference": "TEST-EDUCATION-LICENCE",
            "allowed_use_types": ["education"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "derived_only",
            "allow_item_display": True,
            "allow_item_export": False,
            "allow_trace_item_values": False,
            "valid_from": "2025-01-01",
            "valid_until": None,
            "required_disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "restrictions_i18n": {"uz-Latn": "Faqat ta'lim uchun."},
            "change_reason": "Education eligibility contract test",
        },
    )
    assert licence.status_code == 201, licence.text
    research = prepared["client"].post(
        "/api/v1/researches",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "name": "Education research",
            "purpose": "Validate pinned education context",
            "methodology_version_id": prepared["version"]["id"],
            "pii_mode": "pseudonymous",
            "consent_reference": "EDU-CONSENT",
            "consent_version": "1",
            "retention_policy_id": prepared["policy"]["id"],
            "norm_selection": {},
            "use_type": "education",
        },
    )
    assert research.status_code == 201, research.text
    assert research.json()["use_type"] == "education"
    endpoint = f"/api/v1/methodology-versions/{prepared['version']['id']}"
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    explicit = prepared["client"].get(
        endpoint, params={"use_type": "education"}, headers=headers
    )
    assert explicit.status_code == 200, explicit.text
    pinned = prepared["client"].get(
        endpoint, params={"research_id": research.json()["id"]}, headers=headers
    )
    assert pinned.status_code == 200, pinned.text
    default_research = prepared["client"].get(endpoint, headers=headers)
    assert default_research.status_code == 404
    invalid = prepared["client"].get(
        endpoint, params={"use_type": "unsupported"}, headers=headers
    )
    assert invalid.status_code == 422


def test_registration_is_closed_and_admin_creates_organizations() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        auto_create_schema=True,
        jwt_secret="test-secret-that-is-longer-than-thirty-two-characters",
        bootstrap_enabled=True,
        bootstrap_token=TEST_BOOTSTRAP_TOKEN,
        cors_origins="http://testserver",
    )
    organization = {
        "email": "owner@pilot.example",
        "full_name": "Pilot Owner",
        "password": "A-very-safe-owner-password",
        "organization_name": "Pilot Lab",
        "organization_code": "pilot_lab",
    }
    with TestClient(create_app(settings, Database(settings))) as client:
        closed = client.post("/api/v1/auth/register", json=organization)
        assert closed.status_code == 404
        assert closed.json()["error"]["code"] == "REGISTRATION_DISABLED"

        admin_token = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "email": "admin@example.com",
                "full_name": "Admin",
                "password": "A-secure-bootstrap-password",
                "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
            },
        ).json()["access_token"]
        admin_id = client.get("/api/v1/auth/me", headers=bearer(admin_token)).json()[
            "id"
        ]
        created = client.post(
            "/api/v1/organizations", headers=bearer(admin_token), json=organization
        )
        assert created.status_code == 201, created.text
        assert created.json()["code"] == "pilot_lab"

        owner_token = client.post(
            "/api/v1/auth/login",
            json={"email": organization["email"], "password": organization["password"]},
        ).json()["access_token"]
        membership = client.get("/api/v1/auth/me", headers=bearer(owner_token)).json()[
            "memberships"
        ][0]
        assert membership["organization_id"] == created.json()["id"]
        assert membership["role"] == "owner"

        events = client.get(
            "/api/v1/audit-events",
            headers=bearer(owner_token, membership["organization_id"]),
        ).json()
        assert any(
            event["action"] == "organization.create" and event["actor_id"] == admin_id
            for event in events
        )

        denied = client.post(
            "/api/v1/organizations",
            headers=bearer(owner_token),
            json={
                **organization,
                "email": "x@pilot.example",
                "organization_code": "x_lab",
            },
        )
        assert denied.status_code == 403


def test_csv_import_is_disabled_by_default(prepared) -> None:
    settings = Settings(_env_file=None)
    assert settings.csv_import_enabled is False
    client = prepared["client"]
    client.app.state.settings = settings.model_copy(
        update={"jwt_secret": client.app.state.settings.jwt_secret}
    )
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    research_id = prepared["research"]["id"]
    preview = client.post(
        f"/api/v1/researches/{research_id}/imports/preview",
        headers=headers,
        json={"csv_text": "participant_external_code\nP-001\n"},
    )
    confirm = client.post(
        f"/api/v1/researches/{research_id}/imports/any-id/confirm",
        headers=headers,
        json={"preview_hash": "sha256:x"},
    )
    for response in (preview, confirm):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "CSV_IMPORT_DISABLED"
