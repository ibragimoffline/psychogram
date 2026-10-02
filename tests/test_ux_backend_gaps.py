from __future__ import annotations

import base64
import copy
import json

from pydantic import SecretStr
from sqlalchemy import select

from src.models.domain import AuditEvent, LegalHold, ParticipantPII
from src.services.exports import csv_safe
from tests.conftest import bearer
from tests.conftest import SYNTH_BALANCE_DEMO
from tests.test_api import calculate, create_response


def create_identified_context(env, suffix="one"):
    research = env["client"].post(
        "/api/v1/researches",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={
            "name": f"Identified {suffix}",
            "purpose": "Encrypted PII tests",
            "methodology_version_id": env["version"]["id"],
            "pii_mode": "identified",
            "consent_reference": "CONSENT-TEST",
            "consent_version": "1",
            "retention_policy_id": env["policy"]["id"],
            "norm_selection": {},
            "use_type": "research",
        },
    )
    assert research.status_code == 201, research.text
    research_data = research.json()
    activated = env["client"].post(
        f"/api/v1/researches/{research_data['id']}/activate",
        headers=bearer(env["owner_token"], env["organization_id"]),
    )
    assert activated.status_code == 200, activated.text
    participant = env["client"].post(
        f"/api/v1/researches/{research_data['id']}/participants",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={"external_code": f"PII-{suffix}"},
    )
    assert participant.status_code == 201, participant.text
    return research_data, participant.json()


def test_b01_and_b02_catalog_read_models_and_disclosure(prepared):
    policies = prepared["client"].get(
        "/api/v1/retention-policies",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert policies.status_code == 200
    assert [row["code"] for row in policies.json()] == ["test_365"]

    admin = prepared["client"].get(
        f"/api/v1/methodologies/{prepared['methodology']['id']}",
        headers=bearer(prepared["admin_token"]),
    )
    assert admin.status_code == 200, admin.text
    admin_item = admin.json()["versions"][0]["snapshot"]["items"][1]
    assert "reverse_scoring" in admin_item
    assert admin.json()["source_reference"] == "SYNTHETIC_TEST_ONLY"

    tenant = prepared["client"].get(
        f"/api/v1/methodologies/{prepared['methodology']['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert tenant.status_code == 200, tenant.text
    tenant_item = tenant.json()["versions"][0]["snapshot"]["items"][1]
    assert "reverse_scoring" not in tenant_item
    assert tenant.json()["source_reference"] is None
    assert tenant.json()["versions"][0]["eligible"] is True

    eligible = prepared["client"].get(
        "/api/v1/methodology-versions/eligible",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert [row["id"] for row in eligible.json()] == [prepared["version"]["id"]]
    assert eligible.json()[0]["methodology_code"] == "synth_balance_demo"
    assert eligible.json()[0]["methodology_name"] == "Synthetic Balance Demo"
    assert tenant.json()["versions"][0]["methodology_name"] == "Synthetic Balance Demo"
    history = prepared["client"].get(
        f"/api/v1/methodology-versions/{prepared['version']['id']}/licences",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert history.json()[0]["current"] is True
    assert history.json()[0]["evidence_reference"] is None

    draft_snapshot = copy.deepcopy(SYNTH_BALANCE_DEMO)
    draft_snapshot["version_code"] = "1.0.1"
    draft = prepared["client"].post(
        f"/api/v1/methodologies/{prepared['methodology']['id']}/versions",
        headers=bearer(prepared["admin_token"]),
        json={
            "version_code": "1.0.1",
            "default_locale": "uz-Latn",
            "supported_locales": ["uz-Latn"],
            "target_population": {"adults_only": True, "min_age": 18},
            "estimated_minutes": 5,
            "disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "snapshot": draft_snapshot,
        },
    )
    assert draft.status_code == 201, draft.text
    admin_versions = (
        prepared["client"]
        .get(
            f"/api/v1/methodologies/{prepared['methodology']['id']}/versions",
            headers=bearer(prepared["admin_token"]),
        )
        .json()
    )
    tenant_versions = (
        prepared["client"]
        .get(
            f"/api/v1/methodologies/{prepared['methodology']['id']}/versions",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        )
        .json()
    )
    assert {row["lifecycle_status"] for row in admin_versions} == {
        "draft",
        "published",
    }
    assert [row["lifecycle_status"] for row in tenant_versions] == ["published"]


def test_b03_participant_and_consent_read_models(prepared):
    page = prepared["client"].get(
        f"/api/v1/researches/{prepared['research']['id']}/participants?limit=1",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["external_code"] == "P-001"
    assert "fields" not in page.json()["items"][0]
    detail = prepared["client"].get(
        f"/api/v1/researches/{prepared['research']['id']}"
        f"/participants/{prepared['participant']['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert detail.status_code == 200
    consents = prepared["client"].get(
        f"/api/v1/researches/{prepared['research']['id']}"
        f"/participants/{prepared['participant']['id']}/consents",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert consents.status_code == 200
    assert consents.json()["current"]["status"] == "granted"
    assert consents.json()["history"][0]["record_version"] == 1


def test_b04_response_revision_read_models_and_raw_role_redaction(prepared):
    response = create_response(prepared)
    page = prepared["client"].get(
        f"/api/v1/researches/{prepared['research']['id']}/responses"
        f"?participant_id={prepared['participant']['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert page.status_code == 200
    assert page.json()["items"][0]["current_revision_status"] == "validated"
    detail = prepared["client"].get(
        f"/api/v1/responses/{response['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert detail.json()["current_revision"]["answers"]["q1"] == 2
    history = prepared["client"].get(
        f"/api/v1/responses/{response['id']}/revisions",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert history.json()["revisions"][0]["is_current"] is True

    prepared["client"].post(
        "/api/v1/organizations/current/members",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "email": "auditor@example.com",
            "full_name": "Auditor",
            "password": "A-secure-auditor-password",
            "role": "auditor",
        },
    )
    auditor = (
        prepared["client"]
        .post(
            "/api/v1/auth/login",
            json={
                "email": "auditor@example.com",
                "password": "A-secure-auditor-password",
            },
        )
        .json()["access_token"]
    )
    redacted = prepared["client"].get(
        f"/api/v1/responses/{response['id']}",
        headers=bearer(auditor, prepared["organization_id"]),
    )
    assert redacted.status_code == 200
    assert redacted.json()["current_revision"]["answers"] is None


def test_b05_result_search_filters_and_pagination(prepared):
    response = create_response(prepared)
    result = calculate(prepared, response["current_revision_id"], "result-search")
    assert result.status_code == 200, result.text
    page = prepared["client"].get(
        "/api/v1/results",
        params={
            "research_id": prepared["research"]["id"],
            "participant_id": prepared["participant"]["id"],
            "response_revision_id": response["current_revision_id"],
            "limit": 1,
            "offset": 0,
        },
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["id"] == result.json()["id"]
    empty = prepared["client"].get(
        "/api/v1/results",
        params={"participant_id": "00000000-0000-0000-0000-000000000000"},
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert empty.json()["total"] == 0
    bounded = prepared["client"].get(
        "/api/v1/results?limit=101",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert bounded.status_code == 422


def test_b06_official_json_csv_export_and_unsupported_metadata(prepared):
    response = create_response(prepared)
    result = calculate(
        prepared, response["current_revision_id"], "export-result"
    ).json()
    endpoint = f"/api/v1/results/{result['id']}/export"
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    exported_json = prepared["client"].get(
        endpoint, params={"format": "json"}, headers=headers
    )
    assert exported_json.status_code == 200, exported_json.text
    assert "attachment;" in exported_json.headers["content-disposition"]
    assert exported_json.json()["disclaimer"] == "Bu natija tibbiy tashxis emas."
    exported_csv = prepared["client"].get(
        endpoint, params={"format": "csv"}, headers=headers
    )
    assert exported_csv.status_code == 200
    assert exported_csv.headers["content-type"].startswith("text/csv")
    assert "Bu natija tibbiy tashxis emas." in exported_csv.text
    unsupported = prepared["client"].get(
        endpoint, params={"format": "xlsx"}, headers=headers
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "EXPORT_FORMAT_UNSUPPORTED"
    assert unsupported.json()["error"]["details"]["supported_formats"] == [
        "json",
        "csv",
    ]


def test_formula_safe_csv_cells():
    assert csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert csv_safe("+cmd") == "'+cmd"
    assert csv_safe("normal") == "normal"


def test_b11_pii_aes_gcm_at_rest_view_audit_and_list_separation(prepared):
    research, participant = create_identified_context(prepared)
    endpoint = (
        f"/api/v1/researches/{research['id']}/participants/{participant['id']}/pii"
    )
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    fields = {"full_name": "Sensitive Person", "email": "sensitive@example.com"}
    created = prepared["client"].put(endpoint, headers=headers, json={"fields": fields})
    assert created.status_code == 200, created.text
    assert created.json()["algorithm"] == "AES-256-GCM"
    with prepared["client"].app.state.database.session_factory() as db:
        record = db.scalar(
            select(ParticipantPII).where(
                ParticipantPII.participant_id == participant["id"]
            )
        )
        assert "Sensitive Person" not in record.encrypted_payload
        assert "sensitive@example.com" not in record.encrypted_payload
        assert len(base64.b64decode(record.nonce)) == 12
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.object_type == "participant_pii")
        ).all()
        assert events[-1].safe_metadata == {"field_names": ["email", "full_name"]}
        assert "Sensitive Person" not in json.dumps(events[-1].safe_metadata)
    viewed = prepared["client"].get(endpoint, headers=headers)
    assert viewed.status_code == 200
    assert viewed.json()["fields"] == fields
    updated = prepared["client"].put(
        endpoint,
        headers=headers,
        json={"fields": {"full_name": "Updated Person", "phone": "+998000000"}},
    )
    assert updated.status_code == 200
    assert prepared["client"].get(endpoint, headers=headers).json()["fields"] == {
        "full_name": "Updated Person",
        "phone": "+998000000",
    }
    listed = prepared["client"].get(
        f"/api/v1/researches/{research['id']}/participants",
        headers=headers,
    )
    assert "fields" not in listed.json()["items"][0]
    assert listed.json()["items"][0]["has_pii"] is True


def test_b11_missing_wrong_key_permission_and_cross_tenant_fail_closed(prepared):
    research, participant = create_identified_context(prepared, "failclosed")
    endpoint = (
        f"/api/v1/researches/{research['id']}/participants/{participant['id']}/pii"
    )
    owner_headers = bearer(prepared["owner_token"], prepared["organization_id"])
    settings = prepared["client"].app.state.settings
    original_key = settings.pii_encryption_key
    settings.pii_encryption_key = None
    missing = prepared["client"].put(
        endpoint, headers=owner_headers, json={"fields": {"full_name": "Secret"}}
    )
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "PII_KEY_NOT_CONFIGURED"
    settings.pii_encryption_key = original_key
    assert (
        prepared["client"]
        .put(endpoint, headers=owner_headers, json={"fields": {"full_name": "Secret"}})
        .status_code
        == 200
    )
    settings.pii_encryption_key = SecretStr(base64.b64encode(b"z" * 32).decode("ascii"))
    wrong = prepared["client"].get(endpoint, headers=owner_headers)
    assert wrong.status_code == 503
    assert wrong.json()["error"]["code"] == "PII_DECRYPTION_FAILED"
    settings.pii_encryption_key = original_key

    prepared["client"].post(
        "/api/v1/organizations/current/members",
        headers=owner_headers,
        json={
            "email": "operator-pii@example.com",
            "full_name": "PII Operator",
            "password": "A-secure-operator-password",
            "role": "operator",
            "can_view_pii": True,
        },
    )
    operator = (
        prepared["client"]
        .post(
            "/api/v1/auth/login",
            json={
                "email": "operator-pii@example.com",
                "password": "A-secure-operator-password",
            },
        )
        .json()["access_token"]
    )
    denied = prepared["client"].get(
        endpoint, headers=bearer(operator, prepared["organization_id"])
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PII_ROLE_FORBIDDEN"
    other = (
        prepared["client"]
        .post(
            "/api/v1/auth/register",
            json={
                "email": "pii-other@example.com",
                "full_name": "Other Owner",
                "password": "A-secure-other-owner-password",
                "organization_name": "PII Other",
                "organization_code": "pii_other",
                "org_type": "research_center",
                "region": "GLOBAL",
            },
        )
        .json()
    )
    other_org = (
        prepared["client"]
        .get("/api/v1/auth/me", headers=bearer(other["access_token"]))
        .json()["memberships"][0]["organization_id"]
    )
    cross_tenant = prepared["client"].get(
        endpoint, headers=bearer(other["access_token"], other_org)
    )
    assert cross_tenant.status_code == 404
    assert cross_tenant.json()["error"]["code"] == "RESEARCH_NOT_FOUND"


def test_b11_pii_delete_is_separate_and_legal_hold_blocks(prepared):
    research, participant = create_identified_context(prepared, "delete")
    endpoint = (
        f"/api/v1/researches/{research['id']}/participants/{participant['id']}/pii"
    )
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    assert (
        prepared["client"]
        .put(endpoint, headers=headers, json={"fields": {"full_name": "Delete Me"}})
        .status_code
        == 200
    )
    with prepared["client"].app.state.database.session_factory() as db:
        owner_id = db.scalar(
            select(AuditEvent.actor_id).where(AuditEvent.action == "pii.create")
        )
        hold = LegalHold(
            tenant_id=prepared["organization_id"],
            research_id=research["id"],
            active=True,
            reason="Test hold",
            created_by=owner_id,
        )
        db.add(hold)
        db.commit()
        hold_id = hold.id
    blocked = prepared["client"].delete(endpoint, headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PII_DELETE_LEGAL_HOLD"
    with prepared["client"].app.state.database.session_factory() as db:
        hold = db.get(LegalHold, hold_id)
        hold.active = False
        db.commit()
    deleted = prepared["client"].delete(endpoint, headers=headers)
    assert deleted.status_code == 204
    participant_still_exists = prepared["client"].get(
        f"/api/v1/researches/{research['id']}/participants/{participant['id']}",
        headers=headers,
    )
    assert participant_still_exists.status_code == 200
