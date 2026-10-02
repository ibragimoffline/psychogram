from __future__ import annotations

from datetime import UTC, datetime

from tests.conftest import bearer
from tests.test_api import calculate, create_response, withdraw_consent


def close(env, confirm: bool = False, token: str | None = None):
    return env["client"].post(
        f"/api/v1/researches/{env['research']['id']}/close",
        headers=bearer(token or env["owner_token"], env["organization_id"]),
        json={"confirm_uncalculated": confirm},
    )


def add_participant(env, code: str):
    return env["client"].post(
        f"/api/v1/researches/{env['research']['id']}/participants",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={"external_code": code},
    )


def consent(env, participant_id: str, status: str):
    return env["client"].post(
        f"/api/v1/participants/{participant_id}/consents",
        headers=bearer(env["owner_token"], env["organization_id"]),
        json={
            "status": status,
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )


def test_close_reports_uncalculated_responses_until_confirmed(prepared):
    create_response(prepared)
    blocked = close(prepared)
    assert blocked.status_code == 409
    assert blocked.json()["error"] == {
        "code": "RESEARCH_HAS_UNCALCULATED_RESPONSES",
        "message": blocked.json()["error"]["message"],
        "details": {"uncalculated_responses": 1},
    }

    closed = close(prepared, confirm=True)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert close(prepared).json()["status"] == "closed"

    events = (
        prepared["client"]
        .get(
            "/api/v1/audit-events",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        )
        .json()
    )
    closes = [event for event in events if event["action"] == "research.close"]
    assert [event["safe_metadata"] for event in closes] == [
        {"uncalculated_responses": 1}
    ]


def test_withdrawn_consent_responses_do_not_block_closing(prepared):
    create_response(prepared)
    withdraw_consent(prepared)
    assert close(prepared).status_code == 200


def test_closed_research_blocks_changes_but_keeps_results_readable(prepared):
    client = prepared["client"]
    headers = bearer(prepared["owner_token"], prepared["organization_id"])
    response = create_response(prepared)
    result = calculate(prepared, response["current_revision_id"], "before-close").json()
    other = add_participant(prepared, "P-002").json()
    consent(prepared, other["id"], "granted")
    draft = client.post(
        f"/api/v1/researches/{prepared['research']['id']}/responses",
        headers=headers,
        json={"participant_id": other["id"], "answers": {"q1": 1}},
    ).json()

    assert close(prepared, confirm=True).status_code == 200

    def assert_not_active(reply):
        assert reply.status_code == 409, reply.text
        assert reply.json()["error"]["code"] == "RESEARCH_NOT_ACTIVE"

    assert_not_active(add_participant(prepared, "P-003"))
    assert_not_active(
        client.post(
            f"/api/v1/researches/{prepared['research']['id']}/responses",
            headers=headers,
            json={
                "participant_id": other["id"],
                "attempt_key": "second",
                "answers": {},
            },
        )
    )
    assert_not_active(
        client.post(
            f"/api/v1/responses/{draft['id']}/revisions",
            headers=headers,
            json={"answers": {"q1": 2}, "expected_lock_version": 1},
        )
    )
    assert_not_active(
        client.post(f"/api/v1/responses/{draft['id']}/validate", headers=headers)
    )
    assert_not_active(calculate(prepared, draft["current_revision_id"], "after"))
    # Replaying an existing computation only returns the stored result.
    replay = calculate(prepared, response["current_revision_id"], "after-replay")
    assert replay.status_code == 200
    assert replay.json()["id"] == result["id"]
    assert_not_active(consent(prepared, other["id"], "granted"))

    assert (
        client.get(f"/api/v1/results/{result['id']}", headers=headers).status_code
        == 200
    )
    export = client.get(
        f"/api/v1/results/{result['id']}/export?format=csv", headers=headers
    )
    assert export.status_code == 200
    assert consent(prepared, other["id"], "withdrawn").status_code == 201

    reopened = client.post(
        f"/api/v1/researches/{prepared['research']['id']}/activate", headers=headers
    )
    assert reopened.status_code == 409
    assert reopened.json()["error"]["code"] == "RESEARCH_STATE_INVALID"


def test_operator_cannot_close_research(prepared):
    client = prepared["client"]
    client.post(
        "/api/v1/organizations/current/members",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "email": "operator-close@example.com",
            "full_name": "Operator",
            "password": "A-secure-operator-password",
            "role": "operator",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={
            "email": "operator-close@example.com",
            "password": "A-secure-operator-password",
        },
    ).json()["access_token"]
    denied = close(prepared, token=token)
    assert denied.status_code == 403
