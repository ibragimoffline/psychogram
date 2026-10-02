from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from methodologies.big_five import (
    ANSWER_POINTS,
    FACTORS,
    ITEM_COUNT,
    build_snapshot,
    build_version_payload,
    factor_items,
    item_code,
    points_for,
    subscale_items,
)
from src.services.registry import validate_snapshot
from src.services.scoring_engine import score_snapshot, validate_answers
from tests.conftest import bearer

PRIVATE_TEXTS = Path(__file__).resolve().parents[1] / (
    "methodologies/private/big_five_texts.json"
)
SCORE_FOR_POINTS = {points: answer for answer, points in ANSWER_POINTS.items()}

# The worked example printed in the source ("Тестнинг натижалари"): subscale totals
# A..Y and factor totals. Item answers are not printed, so they are reconstructed
# from these totals; the check covers aggregation, the factor sums and the levels.
SOURCE_EXAMPLE_SUBSCALES = [
    [8, 4, 3, 6, 6],
    [12, 13, 12, 11, 12],
    [6, 6, 11, 14, 13],
    [15, 13, 13, 11, 12],
    [10, 13, 9, 9, 7],
]
SOURCE_EXAMPLE_FACTORS = [27, 60, 50, 64, 48]


def answers_for_subscale_totals(totals: list[list[int]]) -> dict[str, str]:
    answers = {}
    for factor_index, factor_totals in enumerate(totals):
        for block_index, total in enumerate(factor_totals):
            numbers = subscale_items(factor_index, block_index)
            base, extra = divmod(total, 3)
            for position, number in enumerate(numbers):
                points = base + (1 if position < extra else 0)
                answers[item_code(number)] = SCORE_FOR_POINTS[points]
    return answers


def scored(answers: dict[str, str]) -> dict[str, dict]:
    result = score_snapshot(build_snapshot(), answers, "full")
    return {scale["scale_code"]: scale for scale in result["scales"]}


def test_structure_assigns_every_item_to_one_subscale_and_its_factor():
    snapshot = build_snapshot()
    validate_snapshot(snapshot, "uz-Latn")
    assert len(snapshot["items"]) == ITEM_COUNT
    scales = {scale["scale_code"]: scale for scale in snapshot["scales"]}
    kinds = [scale["scale_kind"] for scale in scales.values()]
    assert (kinds.count("factor"), kinds.count("subscale")) == (5, 25)

    seen: list[str] = []
    for factor_index, (code, _label, subscales) in enumerate(FACTORS):
        union: list[str] = []
        for block_index, (sub_code, _sub_label) in enumerate(subscales):
            items = scales[sub_code]["item_codes"]
            assert len(items) == 3
            union += items
            seen += items
        assert sorted(union) == scales[code]["item_codes"]
        assert scales[code]["item_codes"] == [
            item_code(n) for n in factor_items(factor_index)
        ]
    assert sorted(seen) == [item_code(n) for n in range(1, ITEM_COUNT + 1)]
    # Answer sheet in the source: item 1 -> I, 2 -> II, ..., 6 -> I; first 15 -> x.1.
    assert subscale_items(0, 0) == [1, 6, 11]
    assert subscale_items(3, 4) == [64, 69, 74]


@pytest.mark.parametrize(
    ("answer", "factor_score", "factor_band", "subscale_score", "subscale_band"),
    [
        ("-2", 75, "high", 15, "high"),
        ("0", 45, "medium", 9, "medium"),
        ("2", 15, "low", 3, "low"),
    ],
)
def test_uniform_answers_hit_the_scale_extremes_and_middle(
    answer, factor_score, factor_band, subscale_score, subscale_band
):
    scales = scored({item_code(n): answer for n in range(1, ITEM_COUNT + 1)})
    for code, _label, subscales in FACTORS:
        assert scales[code]["score_display"] == str(factor_score)
        assert scales[code]["norm_band_code"] == factor_band
        for sub_code, _sub_label in subscales:
            assert scales[sub_code]["score_display"] == str(subscale_score)
            assert scales[sub_code]["norm_band_code"] == subscale_band


def test_source_worked_example_is_reproduced():
    answers = answers_for_subscale_totals(SOURCE_EXAMPLE_SUBSCALES)
    scales = scored(answers)
    for factor_index, (code, _label, subscales) in enumerate(FACTORS):
        expected = SOURCE_EXAMPLE_FACTORS[factor_index]
        assert scales[code]["score_display"] == str(expected)
        assert points_for(answers, factor_items(factor_index)) == expected
        for block_index, (sub_code, _sub_label) in enumerate(subscales):
            assert scales[sub_code]["score_display"] == str(
                SOURCE_EXAMPLE_SUBSCALES[factor_index][block_index]
            )
    # Levels from the source: 15-35 low, 36-54 medium, 55-75 high.
    assert [scales[code]["norm_band_code"] for code, _l, _s in FACTORS] == [
        "low",
        "high",
        "medium",
        "high",
        "medium",
    ]
    # Subscale levels: A=8 medium, B=4 low, P=15 high, Y=7 medium.
    assert scales["s1_1_activity"]["norm_band_code"] == "medium"
    assert scales["s1_2_dominance"]["norm_band_code"] == "low"
    assert scales["s4_1_anxiety"]["norm_band_code"] == "high"
    assert scales["s5_5_plasticity"]["norm_band_code"] == "medium"


@pytest.mark.parametrize(
    ("subscale_totals", "factor_band"),
    [
        ([7, 7, 7, 7, 7], "low"),  # 35
        ([8, 7, 7, 7, 7], "medium"),  # 36
        ([11, 11, 11, 11, 10], "medium"),  # 54
        ([11, 11, 11, 11, 11], "high"),  # 55
    ],
)
def test_factor_level_boundaries(subscale_totals, factor_band):
    totals = [subscale_totals] + [[9] * 5] * 4
    scales = scored(answers_for_subscale_totals(totals))
    assert scales["f1_extraversion"]["norm_band_code"] == factor_band


@pytest.mark.parametrize(
    ("total", "band"), [(6, "low"), (7, "medium"), (11, "medium"), (12, "high")]
)
def test_subscale_level_boundaries(total, band):
    totals = [[total, 9, 9, 9, 9]] + [[9] * 5] * 4
    assert (
        scored(answers_for_subscale_totals(totals))["s1_1_activity"]["norm_band_code"]
        == band
    )


def test_every_item_is_required_and_answers_are_codes():
    answers = {item_code(n): "0" for n in range(1, ITEM_COUNT + 1)}
    del answers["q40"]
    answers["q41"] = "3"
    issues = validate_answers(build_snapshot(), answers)
    assert {(i["item_code"], i["error_code"]) for i in issues} == {
        ("q40", "ITEM_REQUIRED"),
        ("q41", "OPTION_NOT_ALLOWED"),
    }


@pytest.mark.skipif(not PRIVATE_TEXTS.exists(), reason="licensed texts are local only")
def test_snapshot_with_local_texts_is_valid():
    texts = json.loads(PRIVATE_TEXTS.read_text("utf-8"))
    snapshot = build_snapshot(texts)
    validate_snapshot(snapshot, "uz-Latn")
    assert all("prompt_i18n" in item for item in snapshot["items"])
    assert len(snapshot["interpretations"]) == 10
    assert snapshot["items"][0]["prompt_i18n"]["uz-Latn"].startswith("Chap: Menga")


def test_big_five_runs_through_the_api_and_research_export(prepared):
    client = prepared["client"]
    admin = bearer(prepared["admin_token"])
    owner = bearer(prepared["owner_token"], prepared["organization_id"])
    methodology = client.post(
        "/api/v1/methodologies",
        headers=admin,
        json={
            "methodology_code": "katta_beshlik",
            "canonical_name": "Katta beshlik",
            "purpose_summary": "Shaxsning besh omili",
            "owner_name": "Test",
            "source_reference": "TEST",
        },
    ).json()
    version = client.post(
        f"/api/v1/methodologies/{methodology['id']}/versions",
        headers=admin,
        json=build_version_payload(),
    )
    assert version.status_code == 201, version.text
    version_id = version.json()["id"]
    licence = client.post(
        f"/api/v1/methodology-versions/{version_id}/licences",
        headers=admin,
        json={
            "status": "verified",
            "copyright_status": "permission_granted",
            "rights_holder": "Test",
            "evidence_reference": "TEST",
            "allowed_use_types": ["research"],
            "allowed_org_types": ["research_center"],
            "allowed_regions": ["GLOBAL"],
            "content_disclosure_level": "full",
            "valid_from": str(date.today() - timedelta(days=1)),
            "change_reason": "test",
            "required_disclaimer_i18n": {},
            "restrictions_i18n": {},
        },
    )
    assert licence.status_code == 201, licence.text
    published = client.post(
        f"/api/v1/methodology-versions/{version_id}/publish",
        headers=admin,
        json={"reason": "test"},
    )
    assert published.status_code == 200, published.text
    research = client.post(
        "/api/v1/researches",
        headers=owner,
        json={
            "name": "Big Five",
            "purpose": "test",
            "methodology_version_id": version_id,
            "consent_reference": "C",
            "consent_version": "1",
            "retention_policy_id": prepared["policy"]["id"],
        },
    ).json()
    client.post(f"/api/v1/researches/{research['id']}/activate", headers=owner)
    participant = client.post(
        f"/api/v1/researches/{research['id']}/participants",
        headers=owner,
        json={"external_code": "P001"},
    ).json()
    client.post(
        f"/api/v1/participants/{participant['id']}/consents",
        headers=owner,
        json={
            "status": "granted",
            "reference": "C",
            "version": "1",
            "obtained_at": datetime.now(UTC).isoformat(),
        },
    )
    response = client.post(
        f"/api/v1/researches/{research['id']}/responses",
        headers=owner,
        json={
            "participant_id": participant["id"],
            "answers": answers_for_subscale_totals(SOURCE_EXAMPLE_SUBSCALES),
            "finalize": True,
        },
    ).json()
    assert response["status"] == "validated", response
    result = client.post(
        f"/api/v1/researches/{research['id']}/calculations",
        headers=owner,
        json={
            "response_revision_id": response["current_revision_id"],
            "idempotency_key": "big-five-1",
        },
    )
    assert result.status_code == 200, result.text
    factors = {
        scale["scale_code"]: scale["score_display"]
        for scale in result.json()["scales"]
        if scale["scale_code"].startswith("f")
    }
    assert factors == {
        code: str(score)
        for (code, _l, _s), score in zip(FACTORS, SOURCE_EXAMPLE_FACTORS)
    }

    export = client.get(
        f"/api/v1/researches/{research['id']}/export?format=csv", headers=owner
    )
    table = list(csv.reader(io.StringIO(export.text.lstrip("﻿"))))
    assert "f1_extraversion_score" in table[0]
    assert "s4_1_anxiety_norm_band" in table[0]
    row = dict(zip(table[0], table[1]))
    assert (row["f2_attachment_score"], row["f2_attachment_norm_band"]) == (
        "60",
        "high",
    )
