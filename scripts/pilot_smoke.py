"""End-to-end pilot smoke test against a running API on an EMPTY database.

It bootstraps a platform admin, so it can only run on a fresh database (bootstrap is
refused once any user exists) and never touches a real pilot database. It creates a
synthetic methodology named "SMOKE TEST ONLY"; drop the database afterwards.

Usage:
    PSYCHOGRAM_BOOTSTRAP_TOKEN=... python scripts/pilot_smoke.py --base-url http://127.0.0.1:8000
    (add --with-pii when the server has PSYCHOGRAM_PII_ENCRYPTION_KEY configured)

Exit code 0 means every check passed.
"""

from __future__ import annotations

import argparse
import copy
import csv
import io
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.conftest import SYNTH_BALANCE_DEMO  # noqa: E402

CONSENT = {
    "reference": "SMOKE-CONSENT",
    "version": "1",
    "obtained_at": "2026-01-01T00:00:00Z",
}


class Smoke:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url, timeout=30)
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        print(("PASS" if ok else "FAIL"), name, detail if not ok else "")
        if not ok:
            self.failures.append(name)

    def post(self, path, headers, body=None):
        return self.http.post(
            path, headers=headers, json=body if body is not None else {}
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--with-pii", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("PSYCHOGRAM_BOOTSTRAP_TOKEN")
    if not token:
        print("PSYCHOGRAM_BOOTSTRAP_TOKEN is required")
        return 2
    s = Smoke(args.base_url)
    c = s.http

    s.check("health", c.get("/health").json().get("database") == "reachable")
    boot = c.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "smoke-admin@example.com",
            "full_name": "Smoke Admin",
            "password": "Smoke-admin-password-1",
            "bootstrap_token": token,
        },
    )
    if boot.status_code != 201:
        print(
            "FAIL bootstrap",
            boot.status_code,
            boot.text[:200],
            "(is the database empty?)",
        )
        return 1
    admin = {"Authorization": f"Bearer {boot.json()['access_token']}"}

    org = {
        "email": "smoke-owner@example.com",
        "full_name": "Smoke Owner",
        "password": "Smoke-owner-password-1",
        "organization_name": "Smoke Lab",
        "organization_code": "smoke_lab",
    }
    s.check(
        "admin creates organization",
        s.post("/api/v1/organizations", admin, org).status_code == 201,
    )
    owner_token = c.post(
        "/api/v1/auth/login", json={"email": org["email"], "password": org["password"]}
    ).json()["access_token"]
    org_id = c.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()["memberships"][0]["organization_id"]
    owner = {"Authorization": f"Bearer {owner_token}", "X-Organization-ID": org_id}
    s.post(
        "/api/v1/organizations/current/members",
        owner,
        {
            "email": "smoke-researcher@example.com",
            "full_name": "Smoke Researcher",
            "password": "Smoke-research-password-1",
            "role": "researcher",
            "can_view_pii": True,
        },
    )
    res_token = c.post(
        "/api/v1/auth/login",
        json={
            "email": "smoke-researcher@example.com",
            "password": "Smoke-research-password-1",
        },
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {res_token}", "X-Organization-ID": org_id}

    methodology = s.post(
        "/api/v1/methodologies",
        admin,
        {
            "methodology_code": "smoke_test_only",
            "canonical_name": "SMOKE TEST ONLY",
            "purpose_summary": "Synthetic smoke fixture",
            "owner_name": "Smoke",
            "source_reference": "SYNTHETIC",
        },
    ).json()
    snapshot = copy.deepcopy(SYNTH_BALANCE_DEMO)
    snapshot["methodology_code"] = "smoke_test_only"
    version = s.post(
        f"/api/v1/methodologies/{methodology['id']}/versions",
        admin,
        {
            "version_code": "1.0.0",
            "estimated_minutes": 5,
            "disclaimer_i18n": {"uz-Latn": "Bu natija tibbiy tashxis emas."},
            "snapshot": snapshot,
        },
    ).json()
    s.post(
        f"/api/v1/methodology-versions/{version['id']}/licences",
        admin,
        {
            "status": "verified",
            "copyright_status": "public_domain",
            "rights_holder": "Smoke",
            "evidence_reference": "SYNTHETIC",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "full",
            "allow_item_display": True,
            "allow_trace_item_values": True,
            "valid_from": "2026-01-01",
            "change_reason": "smoke",
            "required_disclaimer_i18n": {},
            "restrictions_i18n": {},
        },
    )
    published = s.post(
        f"/api/v1/methodology-versions/{version['id']}/publish",
        admin,
        {"reason": "smoke"},
    )
    s.check(
        "publish methodology (UPDATE methodology_versions)",
        published.status_code == 200,
        published.text[:200],
    )
    policy = s.post(
        "/api/v1/retention-policies",
        owner,
        {"code": "smoke_days", "retention_days": 30},
    ).json()

    def new_research(name: str, pii_mode: str) -> str:
        research = s.post(
            "/api/v1/researches",
            h,
            {
                "name": name,
                "purpose": "Smoke",
                "methodology_version_id": version["id"],
                "pii_mode": pii_mode,
                "consent_reference": "SMOKE-CONSENT",
                "consent_version": "1",
                "retention_policy_id": policy["id"],
                "use_type": "research",
                "norm_selection": {},
            },
        ).json()
        started = s.post(f"/api/v1/researches/{research['id']}/activate", h)
        s.check(
            f"start research {name} (UPDATE researches)",
            started.json().get("status") == "active",
            started.text[:200],
        )
        return research["id"]

    rid = new_research("Smoke", "pseudonymous")

    def respondent(code: str, answers: dict) -> tuple[str, dict]:
        participant = s.post(
            f"/api/v1/researches/{rid}/participants", h, {"external_code": code}
        ).json()
        s.post(
            f"/api/v1/participants/{participant['id']}/consents",
            h,
            {"status": "granted", **CONSENT},
        )
        response = s.post(
            f"/api/v1/researches/{rid}/responses",
            h,
            {
                "participant_id": participant["id"],
                "answers": answers,
                "finalize": False,
            },
        ).json()
        return participant["id"], response

    _, draft = respondent("S001", {"q1": 3, "q2": 9})
    failed = s.post(f"/api/v1/responses/{draft['id']}/validate", h).json()
    s.check(
        "validation issue next to item (UPDATE response_revisions)",
        failed.get("validation_issues")
        == [{"item_code": "q2", "error_code": "VALUE_OUT_OF_RANGE", "safe_params": {}}],
    )
    fixed = s.post(
        f"/api/v1/responses/{draft['id']}/revisions",
        h,
        {
            "answers": {"q1": 3, "q2": 0, "q3": 3, "q4": 0},
            "expected_lock_version": draft["lock_version"],
        },
    ).json()
    s.check("revise draft (UPDATE responses)", fixed.get("revision_number") == 2)
    s.post(f"/api/v1/responses/{draft['id']}/validate", h)
    key = {
        "response_revision_id": fixed["id"],
        "idempotency_key": f"calc-{fixed['id']}",
    }
    first = s.post(f"/api/v1/researches/{rid}/calculations", h, key).json()
    again = s.post(f"/api/v1/researches/{rid}/calculations", h, key).json()
    s.check(
        "score (UPDATE calculation_runs)",
        first.get("scales", [{}])[0].get("score_display") == "10.00",
    )
    s.check(
        "idempotent retry returns the same result", first.get("id") == again.get("id")
    )

    _, second = respondent("S002", {"q1": 0, "q2": 3, "q3": 0, "q4": 3})
    s.post(f"/api/v1/responses/{second['id']}/validate", h)
    detail = c.get(f"/api/v1/responses/{second['id']}", headers=h).json()
    s.post(
        f"/api/v1/researches/{rid}/calculations",
        h,
        {
            "response_revision_id": detail["current_revision_id"],
            "idempotency_key": f"calc-{detail['current_revision_id']}",
        },
    )
    respondent("S003", {"q1": 1})  # left uncalculated on purpose

    export = c.get(f"/api/v1/researches/{rid}/export?format=csv", headers=h)
    rows = list(csv.reader(io.StringIO(export.content.decode("utf-8-sig"))))
    s.check(
        "research CSV export",
        export.status_code == 200
        and [r[0] for r in rows[1:]] == ["S001", "S002"]
        and export.headers.get("x-export-not-calculated") == "1",
        export.text[:200],
    )

    blocked = s.post(f"/api/v1/researches/{rid}/close", h, {})
    s.check(
        "close reports uncalculated responses",
        blocked.status_code == 409
        and blocked.json()["error"].get("details") == {"uncalculated_responses": 1},
    )
    closed = s.post(
        f"/api/v1/researches/{rid}/close", h, {"confirm_uncalculated": True}
    )
    s.check("close research", closed.json().get("status") == "closed")
    refused = s.post(
        f"/api/v1/researches/{rid}/participants", h, {"external_code": "S004"}
    )
    s.check("closed research refuses new respondents", refused.status_code == 409)
    s.check(
        "result readable after close",
        c.get(f"/api/v1/results/{first['id']}", headers=h).status_code == 200,
    )

    if args.with_pii:
        pii_research = new_research("Smoke PII", "identified")
        participant = s.post(
            f"/api/v1/researches/{pii_research}/participants",
            h,
            {"external_code": "PII-1"},
        ).json()
        url = f"/api/v1/researches/{pii_research}/participants/{participant['id']}/pii"
        stored = c.put(url, headers=h, json={"fields": {"full_name": "Smoke Person"}})
        updated = c.put(
            url, headers=h, json={"fields": {"full_name": "Smoke Person 2"}}
        )
        removed = c.delete(url, headers=h)
        s.check(
            "PII store, update, delete (UPDATE/DELETE participant_pii)",
            (stored.status_code, updated.status_code, removed.status_code)
            == (200, 200, 204),
            f"{stored.status_code} {updated.status_code} {removed.status_code}",
        )

    audit = c.get("/api/v1/audit-events", headers=owner).json()
    s.check("audit trail written", any(e["action"] == "research.close" for e in audit))

    print(f"\n{'OK' if not s.failures else 'FAILED'}: {len(s.failures)} failure(s)")
    return 1 if s.failures else 0


if __name__ == "__main__":
    sys.exit(main())
