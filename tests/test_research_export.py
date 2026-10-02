from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from tests.conftest import bearer
from tests.test_api import calculate, create_response, revoke_licence

HEADER = [
    "participant_code",
    "methodology_code",
    "version_code",
    "response_revision",
    "result_id",
    "calculated_at",
    "total_score",
    "total_validity_status",
    "total_norm_band",
    "total_interpretation_code",
]


def export(env, token: str | None = None, organization_id: str | None = None):
    return env["client"].get(
        f"/api/v1/researches/{env['research']['id']}/export?format=csv",
        headers=bearer(
            token or env["owner_token"], organization_id or env["organization_id"]
        ),
    )


def rows(reply) -> list[list[str]]:
    assert reply.text.startswith("﻿")
    return list(csv.reader(io.StringIO(reply.text.lstrip("﻿"))))


def respondent(env, code: str, answers: dict | None = None, consent: str = "granted"):
    client = env["client"]
    headers = bearer(env["owner_token"], env["organization_id"])
    participant = client.post(
        f"/api/v1/researches/{env['research']['id']}/participants",
        headers=headers,
        json={"external_code": code},
    ).json()
    client.post(
        f"/api/v1/participants/{participant['id']}/consents",
        headers=headers,
        json={
            "status": consent,
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    return create_response({**env, "participant": participant}, answers)


def test_export_has_one_row_per_current_result_and_reports_the_rest(prepared):
    first = create_response(prepared)
    result = calculate(prepared, first["current_revision_id"], "export-1").json()
    respondent(prepared, "P-002")  # validated, never calculated
    withdrawn = respondent(prepared, "P-003")
    calculate(prepared, withdrawn["current_revision_id"], "export-3")
    prepared["client"].post(
        f"/api/v1/participants/{withdrawn['participant_id']}/consents",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "status": "withdrawn",
            "reference": "CONSENT-TEST",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )

    reply = export(prepared)
    assert reply.status_code == 200, reply.text
    assert reply.headers["content-type"] == "text/csv; charset=utf-8"
    assert reply.headers["cache-control"] == "no-store, private"
    assert "\r\n" in reply.text
    assert reply.headers["x-export-rows"] == "1"
    assert reply.headers["x-export-not-calculated"] == "1"
    assert reply.headers["x-export-excluded-consent"] == "1"
    table = rows(reply)
    assert table[0] == HEADER
    assert table[1:] == [
        [
            "P-001",
            "synth_balance_demo",
            "1.0.0",
            "1",
            result["id"],
            table[1][5],
            "5.00",
            "valid",
            "demo_middle",
            "demo_middle_text",
        ]
    ]

    events = (
        prepared["client"]
        .get(
            "/api/v1/audit-events",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        )
        .json()
    )
    assert [e["safe_metadata"] for e in events if e["action"] == "research.export"] == [
        {"format": "csv", "rows": 1, "not_calculated": 1, "excluded_consent": 1}
    ]


def test_corrected_answers_are_not_exported_with_the_old_result(prepared):
    response = create_response(prepared)
    calculate(prepared, response["current_revision_id"], "before-fix")
    prepared["client"].post(
        f"/api/v1/responses/{response['id']}/revisions",
        headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        json={
            "answers": {"q1": 3, "q2": 0, "q3": 3, "q4": 0},
            "correction_reason": "Kiritishdagi xato",
            "expected_lock_version": response["lock_version"],
            "finalize": True,
        },
    )
    stale = export(prepared)
    assert stale.headers["x-export-rows"] == "0"
    assert stale.headers["x-export-not-calculated"] == "1"

    current = (
        prepared["client"]
        .get(
            f"/api/v1/responses/{response['id']}",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
        )
        .json()
    )
    calculate(prepared, current["current_revision_id"], "after-fix")
    table = rows(export(prepared))
    assert [(row[0], row[3], row[6]) for row in table[1:]] == [("P-001", "2", "10.00")]


def test_export_neutralizes_formula_codes_but_keeps_scores_numeric(prepared):
    response = respondent(prepared, "=HYPERLINK(1)")
    calculate(prepared, response["current_revision_id"], "formula")
    table = rows(export(prepared))
    assert table[1][0] == "'=HYPERLINK(1)"
    assert table[1][6] == "5.00"


def test_export_includes_every_respondent_beyond_page_size(prepared):
    total = 105
    for index in range(total):
        response = respondent(prepared, f"B-{index:03d}")
        calculate(prepared, response["current_revision_id"], f"bulk-{index}")
    reply = export(prepared)
    assert reply.headers["x-export-rows"] == str(total)
    codes = [row[0] for row in rows(reply)[1:]]
    assert codes == [f"B-{index:03d}" for index in range(total)]


def test_export_is_refused_when_the_licence_is_revoked(prepared):
    response = create_response(prepared)
    calculate(prepared, response["current_revision_id"], "licensed")
    revoke_licence(prepared)
    reply = export(prepared)
    assert reply.status_code == 409
    assert reply.json()["error"]["code"] == "LICENCE_NOT_VALID"


def test_export_respects_roles_and_tenant(prepared):
    client = prepared["client"]
    for role in ("auditor", "operator"):
        client.post(
            "/api/v1/organizations/current/members",
            headers=bearer(prepared["owner_token"], prepared["organization_id"]),
            json={
                "email": f"{role}-research-export@example.com",
                "full_name": role,
                "password": f"A-secure-{role}-password",
                "role": role,
            },
        )
        token = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"{role}-research-export@example.com",
                "password": f"A-secure-{role}-password",
            },
        ).json()["access_token"]
        assert export(prepared, token=token).status_code == 403

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-export@example.com",
            "full_name": "Other",
            "password": "A-very-safe-other-password",
            "organization_name": "Other",
            "organization_code": "other_export",
        },
    ).json()["access_token"]
    other_org = client.get("/api/v1/auth/me", headers=bearer(other)).json()[
        "memberships"
    ][0]["organization_id"]
    assert export(prepared, token=other, organization_id=other_org).status_code == 404
