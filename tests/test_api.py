from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from src.models.domain import ResearchMethodologyPin, ResponseRevision
from tests.conftest import TEST_BOOTSTRAP_TOKEN, bearer


def create_response(env, answers=None):
    response = env["client"].post(
        f"/api/v1/researches/{env['research']['id']}/responses",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={
            "participant_id": env["participant"]["id"],
            "answers": answers or {"q1": 2, "q2": 3, "q3": 1, "q4": 0},
            "finalize": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def calculate(env, revision_id, key="calculation-key-1"):
    return env["client"].post(
        f"/api/v1/researches/{env['research']['id']}/calculations",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={"response_revision_id": revision_id, "idempotency_key": key},
    )


def test_health_and_bootstrap_is_one_time(client: TestClient):
    assert client.get("/health").json() == {
        "status": "healthy",
        "database": "reachable",
    }
    payload = {
        "email": "admin@example.com",
        "full_name": "Admin",
        "password": "A-secure-bootstrap-password",
        "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
    }
    first = client.post("/api/v1/auth/bootstrap", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/auth/bootstrap", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "BOOTSTRAP_ALREADY_COMPLETED"
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(first.json()["access_token"])
        ).status_code
        == 200
    )


def test_bootstrap_rejects_invalid_token_before_one_time_state(client: TestClient):
    payload = {
        "email": "attacker@example.com",
        "full_name": "Attacker",
        "password": "A-secure-bootstrap-password",
        "bootstrap_token": "x" * len(TEST_BOOTSTRAP_TOKEN),
    }
    denied = client.post("/api/v1/auth/bootstrap", json=payload)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "BOOTSTRAP_TOKEN_INVALID"


def test_login_failure_is_generic_for_missing_and_existing_users(client: TestClient):
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "known@example.com",
            "full_name": "Known User",
            "password": "A-secure-known-password",
            "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
        },
    )
    assert bootstrap.status_code == 201
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong"},
    )
    existing = client.post(
        "/api/v1/auth/login",
        json={"email": "known@example.com", "password": "wrong"},
    )
    assert missing.status_code == existing.status_code == 401
    assert (
        missing.json()["error"]
        == existing.json()["error"]
        == {
            "code": "AUTH_CREDENTIALS_INVALID",
            "message": "Email or password is invalid",
        }
    )


def test_scoring_disclaimer_and_idempotency(prepared):
    response = create_response(prepared)
    first = calculate(prepared, response["current_revision_id"])
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["scales"][0]["aggregate_score_unrounded"] == "6"
    assert result["scales"][0]["score_display"] == "5.00"
    assert result["scales"][0]["norm_band_code"] == "demo_middle"
    assert result["disclaimer_i18n"]["uz-Latn"] == "Bu natija tibbiy tashxis emas."
    second = calculate(prepared, response["current_revision_id"])
    assert second.status_code == 200
    assert second.json()["id"] == result["id"]


def test_rbac_and_cross_tenant_denial(prepared):
    response = create_response(prepared)
    member = prepared["client"].post(
        "/api/v1/organizations/current/members",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "email": "operator@example.com",
            "full_name": "Operator",
            "password": "A-secure-operator-password",
            "role": "operator",
        },
    )
    assert member.status_code == 201, member.text
    operator_token = (
        prepared["client"]
        .post(
            "/api/v1/auth/login",
            json={
                "email": "operator@example.com",
                "password": "A-secure-operator-password",
            },
        )
        .json()["access_token"]
    )
    denied = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/calculations",
        headers=bearer(operator_token, prepared["organization_id"]),
        json={
            "response_revision_id": response["current_revision_id"],
            "idempotency_key": "operator-denied",
        },
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_FORBIDDEN"
    other = (
        prepared["client"]
        .post(
            "/api/v1/auth/register",
            json={
                "email": "other@example.com",
                "full_name": "Other",
                "password": "A-secure-other-owner-password",
                "organization_name": "Other Org",
                "organization_code": "other_org",
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
    cross = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/activate",
        headers=bearer(other["access_token"], other_org),
    )
    assert cross.status_code == 404
    assert cross.json()["error"]["code"] == "RESEARCH_NOT_FOUND"


def test_consent_and_research_pin_gates(prepared):
    participant = (
        prepared["client"]
        .post(
            f"/api/v1/researches/{prepared['research']['id']}/participants",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
            json={"external_code": "P-NO-CONSENT"},
        )
        .json()
    )
    blocked = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/responses",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "participant_id": participant["id"],
            "answers": {"q1": 1},
            "finalize": False,
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CONSENT_NOT_VALID"
    response = create_response(prepared)
    with prepared["client"].app.state.database.session_factory() as db:
        pin = db.scalar(
            select(ResearchMethodologyPin).where(
                ResearchMethodologyPin.research_id == prepared["research"]["id"]
            )
        )
        db.execute(
            update(ResearchMethodologyPin)
            .where(ResearchMethodologyPin.id == pin.id)
            .values(methodology_content_hash="sha256:" + "0" * 64)
        )
        db.commit()
    mismatch = calculate(prepared, response["current_revision_id"], "hash-mismatch")
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "METHODOLOGY_HASH_MISMATCH"


def test_revision_immutability_and_idempotency_reuse(prepared):
    response = create_response(prepared)
    first = calculate(prepared, response["current_revision_id"], "stable-client-key")
    assert first.status_code == 200, first.text
    revised = prepared["client"].post(
        f"/api/v1/responses/{response['id']}/revisions",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "answers": {"q1": 3, "q2": 0, "q3": 1, "q4": 0},
            "correction_reason": "Operator correction",
            "expected_lock_version": response["lock_version"],
            "finalize": True,
        },
    )
    assert revised.status_code == 201, revised.text
    reused = calculate(prepared, revised.json()["id"], "stable-client-key")
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    old = prepared["client"].get(
        f"/api/v1/results/{first.json()['id']}",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
    )
    assert old.json()["scales"][0]["score_display"] == "5.00"
    with prepared["client"].app.state.database.session_factory() as db:
        original = db.get(ResponseRevision, response["current_revision_id"])
        assert original.answers == {"q1": 2, "q2": 3, "q3": 1, "q4": 0}
        assert original.status == "validated"


def test_revoked_licence_blocks_new_scoring(prepared):
    response = create_response(prepared)
    licence = prepared["client"].post(
        f"/api/v1/methodology-versions/{prepared['version']['id']}/licences",
        headers=bearer(prepared["admin_token"]),
        json={
            "status": "revoked",
            "copyright_status": "public_domain",
            "rights_holder": "Synthetic",
            "evidence_reference": "SYNTHETIC_TEST_ONLY",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "summary_only",
            "valid_from": str(date.today() - timedelta(days=1)),
            "required_disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "restrictions_i18n": {"uz-Latn": "Revoked"},
            "change_reason": "Test revocation",
        },
    )
    assert licence.status_code == 201, licence.text
    blocked = calculate(prepared, response["current_revision_id"], "revoked-licence")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "LICENCE_NOT_VALID"


def test_withdrawn_consent_and_invalid_revision_block_scoring(prepared):
    response = create_response(prepared)
    withdrawn = prepared["client"].post(
        f"/api/v1/participants/{prepared['participant']['id']}/consents",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "status": "withdrawn",
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    assert withdrawn.status_code == 201
    blocked = calculate(prepared, response["current_revision_id"], "withdrawn-consent")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CONSENT_NOT_VALID"


def withdraw_consent(env):
    withdrawn = env["client"].post(
        f"/api/v1/participants/{env['participant']['id']}/consents",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={
            "status": "withdrawn",
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    assert withdrawn.status_code == 201, withdrawn.text


def revoke_licence(env):
    licence = env["client"].post(
        f"/api/v1/methodology-versions/{env['version']['id']}/licences",
        headers=bearer(env["admin_token"]),
        json={
            "status": "revoked",
            "copyright_status": "public_domain",
            "rights_holder": "Synthetic",
            "evidence_reference": "SYNTHETIC_TEST_ONLY",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "summary_only",
            "valid_from": str(date.today() - timedelta(days=1)),
            "required_disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "restrictions_i18n": {"uz-Latn": "Revoked"},
            "change_reason": "Test revocation",
        },
    )
    assert licence.status_code == 201, licence.text


def test_withdrawn_consent_blocks_cached_calculation_and_result_read(prepared):
    revision_id = create_response(prepared)["current_revision_id"]
    first = calculate(prepared, revision_id, "cached-consent")
    assert first.status_code == 200, first.text
    result_url = f"/api/v1/results/{first.json()['id']}"
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    assert prepared["client"].get(result_url, headers=headers).status_code == 200

    withdraw_consent(prepared)

    replay = calculate(prepared, revision_id, "cached-consent")
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "CONSENT_NOT_VALID"
    other_key = calculate(prepared, revision_id, "cached-consent-new-key")
    assert other_key.status_code == 409
    assert other_key.json()["error"]["code"] == "CONSENT_NOT_VALID"
    read = prepared["client"].get(result_url, headers=headers)
    assert read.status_code == 409
    assert read.json()["error"]["code"] == "CONSENT_NOT_VALID"
    export = prepared["client"].get(f"{result_url}/export?format=csv", headers=headers)
    assert export.status_code == 409
    assert export.json()["error"]["code"] == "CONSENT_NOT_VALID"


def test_revoked_licence_blocks_cached_calculation_and_result_read(prepared):
    revision_id = create_response(prepared)["current_revision_id"]
    first = calculate(prepared, revision_id, "cached-licence")
    assert first.status_code == 200, first.text
    result_url = f"/api/v1/results/{first.json()['id']}"
    headers = bearer(prepared["owner_token"], prepared["organization_id"])

    revoke_licence(prepared)

    replay = calculate(prepared, revision_id, "cached-licence")
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "LICENCE_NOT_VALID"
    read = prepared["client"].get(result_url, headers=headers)
    assert read.status_code == 409
    assert read.json()["error"]["code"] == "LICENCE_NOT_VALID"


def test_duplicate_participant_code_is_conflict_not_server_error(prepared):
    client = prepared["client"]
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    duplicate = client.post(
        f"/api/v1/researches/{prepared['research']['id']}/participants",
        headers=headers,
        json={"external_code": prepared["participant"]["external_code"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PARTICIPANT_CODE_EXISTS"

    other_research = client.post(
        "/api/v1/researches",
        headers=headers,
        json={
            "name": "Second study",
            "purpose": "Codes are scoped per research",
            "methodology_version_id": prepared["version"]["id"],
            "consent_reference": "CONSENT-TEST",
            "consent_version": "1",
            "retention_policy_id": prepared["policy"]["id"],
        },
    ).json()
    client.post(f"/api/v1/researches/{other_research['id']}/activate", headers=headers)
    same_code = client.post(
        f"/api/v1/researches/{other_research['id']}/participants",
        headers=headers,
        json={"external_code": prepared["participant"]["external_code"]},
    )
    assert same_code.status_code == 201, same_code.text


def test_duplicate_retention_code_is_conflict_not_server_error(prepared):
    client = prepared["client"]
    duplicate = client.post(
        "/api/v1/retention-policies",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={"code": prepared["policy"]["code"], "retention_days": 30},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RETENTION_POLICY_CODE_EXISTS"

    other_token = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-owner@example.com",
            "full_name": "Other Owner",
            "password": "A-very-safe-other-password",
            "organization_name": "Other Lab",
            "organization_code": "other_lab",
        },
    ).json()["access_token"]
    other_org = client.get("/api/v1/auth/me", headers=bearer(other_token)).json()[
        "memberships"
    ][0]["organization_id"]
    same_code = client.post(
        "/api/v1/retention-policies",
        headers=bearer(other_token, other_org),
        json={"code": prepared["policy"]["code"], "retention_days": 30},
    )
    assert same_code.status_code == 201, same_code.text


def test_validation_issues_are_returned_per_item(prepared):
    client = prepared["client"]
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    created = client.post(
        f"/api/v1/researches/{prepared['research']['id']}/responses",
        headers=headers,
        json={
            "participant_id": prepared["participant"]["id"],
            "answers": {"q1": 9, "q2": "two", "q3": 1, "q9": 1},
        },
    )
    assert created.status_code == 201, created.text
    response_id = created.json()["id"]
    expected = [
        {"item_code": "q1", "error_code": "VALUE_OUT_OF_RANGE", "safe_params": {}},
        {"item_code": "q2", "error_code": "TYPE_INVALID", "safe_params": {}},
        {"item_code": "q9", "error_code": "UNKNOWN_ITEM", "safe_params": {}},
    ]

    validated = client.post(
        f"/api/v1/responses/{response_id}/validate", headers=headers
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "validation_failed"
    assert validated.json()["validation_issues"] == expected

    again = client.post(f"/api/v1/responses/{response_id}/validate", headers=headers)
    assert again.json()["validation_issues"] == expected
    assert again.json()["validation_summary"]["error_count"] == 3

    detail = client.get(f"/api/v1/responses/{response_id}", headers=headers).json()
    assert detail["current_revision"]["validation_issues"] == expected
    history = client.get(
        f"/api/v1/responses/{response_id}/revisions", headers=headers
    ).json()
    assert history["revisions"][0]["validation_issues"] == expected

    fixed = client.post(
        f"/api/v1/responses/{response_id}/revisions",
        headers=headers,
        json={
            "answers": {"q1": 3, "q2": 2, "q3": 1},
            "correction_reason": "Fix entry",
            "expected_lock_version": 1,
            "finalize": True,
        },
    )
    assert fixed.status_code == 201, fixed.text
    assert fixed.json()["status"] == "validated"
    assert fixed.json()["validation_issues"] == []


def test_summary_only_licence_redacts_item_trace(prepared):
    licence = prepared["client"].post(
        f"/api/v1/methodology-versions/{prepared['version']['id']}/licences",
        headers=bearer(prepared["admin_token"]),
        json={
            "status": "verified",
            "copyright_status": "public_domain",
            "rights_holder": "Synthetic",
            "evidence_reference": "SYNTHETIC_TEST_ONLY",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "summary_only",
            "allow_trace_item_values": False,
            "valid_from": str(date.today() - timedelta(days=1)),
            "valid_until": str(date.today() + timedelta(days=10)),
            "required_disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "restrictions_i18n": {"uz-Latn": "Summary only"},
            "change_reason": "Disclosure test",
        },
    )
    assert licence.status_code == 201, licence.text
    response = create_response(prepared)
    result = calculate(prepared, response["current_revision_id"], "summary-licence")
    assert result.status_code == 200, result.text
    assert result.json()["scales"][0]["disclosure_level_applied"] == "summary_only"
    assert all(
        not step.get("entity_ref") or step["entity_ref"].get("kind") != "item"
        for step in result.json()["trace"]
    )


def test_csv_preview_confirm_pii_and_duplicate_denial(prepared):
    participant = (
        prepared["client"]
        .post(
            f"/api/v1/researches/{prepared['research']['id']}/participants",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
            json={"external_code": "P-CSV"},
        )
        .json()
    )
    prepared["client"].post(
        f"/api/v1/participants/{participant['id']}/consents",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "status": "granted",
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    template = prepared["version"]["template_id"]
    header = (
        "_methodology_code,_version_code,_template_id,"
        "participant_external_code,attempt_key,"
        "item.q1,item.q2,item.q3,item.q4\n"
    )
    row = f"synth_balance_demo,1.0.0,{template},P-CSV,initial,2,3,1,0\n"
    preview = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/imports/preview",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={"csv_text": header + row},
    )
    assert preview.status_code == 201, preview.text
    assert preview.json()["summary"]["valid_rows"] == 1
    confirm_path = (
        f"/api/v1/researches/{prepared['research']['id']}/imports/"
        f"{preview.json()['import_id']}/confirm"
    )
    confirm = prepared["client"].post(
        confirm_path,
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={"preview_hash": preview.json()["preview_hash"]},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["summary"]["accepted_rows"] == 1
    pii = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/imports/preview",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={"csv_text": (header + row).replace("attempt_key,", "email,attempt_key,")},
    )
    assert pii.status_code == 400
    assert pii.json()["error"]["code"] == "PII_COLUMN_FORBIDDEN"
    duplicate = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/imports/preview",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={"csv_text": header + row + row},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["summary"]["duplicate_rows"] == 2
    invalid_integer = prepared["client"].post(
        f"/api/v1/researches/{prepared['research']['id']}/imports/preview",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "csv_text": header
            + f"synth_balance_demo,1.0.0,{template},P-001,new_attempt,2,3.0,1,0\n"
        },
    )
    assert invalid_integer.status_code == 201
    assert "TYPE_INVALID" in {
        error["error_code"] for error in invalid_integer.json()["errors"]
    }
