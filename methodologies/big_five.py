"""Katta beshlik (Big Five) questionnaire: structure, scoring key and norms.

Source: the Uzbek-Cyrillic package received on 2026-10-02 (docs/13_big_five_intake.md).
75 bipolar statement pairs answered on -2..2; every answer maps to 5..1 points
(-2 = the left statement fits strongly). Item n belongs to factor ((n - 1) % 5) + 1
and to subscale block ((n - 1) // 15) + 1, so each subscale has 3 items and each
factor 15.

Only the structure lives here. The statement and interpretation texts are licensed
content and stay out of the repository: scripts/extract_big_five_texts.py writes them
to methodologies/private/, and build_version_payload() merges them in when present.
"""

from __future__ import annotations

import re
from typing import Any

METHODOLOGY_CODE = "katta_beshlik"
VERSION_CODE = "1.0.0"
ITEM_COUNT = 75

# (scale_code, label in the source's Uzbek Cyrillic). Labels marked in the intake
# document were tidied (typos) and need the methodology owner's confirmation.
FACTORS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "f1_extraversion",
        "Экстраверсия – интроверсия",
        [
            ("s1_1_activity", "Фаоллик – пассивлик"),
            ("s1_2_dominance", "Ҳукмронлик – тобелик"),
            ("s1_3_sociability", "Киришимлилик – тундлик"),
            ("s1_4_sensation_seeking", "Таассуротлар излаш – таассуротлардан қочиш"),
            ("s1_5_attention_seeking", "Намоён қилиш – айбдорлик ҳиссидан қочиш"),
        ],
    ),
    (
        "f2_attachment",
        "Меҳрибонлик – алоҳидалик",
        [
            ("s2_1_warmth", "Самимийлик – бепарволик"),
            ("s2_2_cooperation", "Ҳамкорлик – рақобатдошлик"),
            ("s2_3_trust", "Ишонувчанлик – шубҳаланувчанлик"),
            ("s2_4_understanding", "Тушуниш – тушунмаслик"),
            ("s2_5_respect", "Бошқаларни эъзозлаш – ўзини ўзи эъзозлаш"),
        ],
    ),
    (
        "f3_self_control",
        "Ўзини ўзи назорат қилиш – ғайри ихтиёрийлик",
        [
            ("s3_1_orderliness", "Батартиблик – бетартиблик"),
            ("s3_2_perseverance", "Қатъиятлилик – қатъиятсизлик"),
            ("s3_3_responsibility", "Масъулиятлилик – масъулиятсизлик"),
            ("s3_4_impulse_control", "Хулқ-атворни ўзи назорат қилиш – импульсивлик"),
            ("s3_5_prudence", "Эҳтиёткорлик – бепарволик"),
        ],
    ),
    (
        # High scores mean emotional instability (the left statements describe it).
        "f4_emotional_instability",
        "Эмоционал беқарорлик – эмоционал барқарорлик",
        [
            ("s4_1_anxiety", "Хавотирланиш – беғамлик"),
            ("s4_2_tension", "Кескинлик – бўшашганлик"),
            ("s4_3_depressiveness", "Депрессивлик – эмоционал қулайлик"),
            ("s4_4_self_criticism", "Ўзига ўзи танқидий – ўзига ўзи етарлилик"),
            ("s4_5_lability", "Эмоционал лабиллик – эмоционал стабиллик"),
        ],
    ),
    (
        "f5_expressiveness",
        "Таъсирчанлик – ишчанлик",
        [
            ("s5_1_curiosity", "Синчковлик – консерватизм"),
            (
                "s5_2_imagination",
                "Билимга қизиқувчанлик – амалий нуқтаи назардан қараш (реалист)",
            ),
            ("s5_3_artistry", "Моҳирлик (артистиклик) – артистикликнинг етишмаслиги"),
            ("s5_4_sensitivity", "Сезгирлик (сенситивлик) – сезгирликнинг йўқлиги"),
            ("s5_5_plasticity", "Нафислик (пластиклик) – ригидлик"),
        ],
    ),
]

# Answer -2..2 -> points 5..1 for every item ("Баҳолаш шкаласи" table in the source).
ANSWER_POINTS = {"-2": 5, "-1": 4, "0": 3, "1": 2, "2": 1}
ANSWER_LABELS = {
    "-2": ("-2 · chap mulohaza kuchli", "-2 · чап мулоҳаза кучли"),
    "-1": ("-1 · chap mulohaza kuchsiz", "-1 · чап мулоҳаза кучсиз"),
    "0": ("0 · teng yoki hech biri", "0 · тенг ёки ҳеч бири"),
    "1": ("1 · o‘ng mulohaza kuchsiz", "1 · ўнг мулоҳаза кучсиз"),
    "2": ("2 · o‘ng mulohaza kuchli", "2 · ўнг мулоҳаза кучли"),
}

# Levels stated in the source ("Беш омилли тестнинг натижалари тавсифи").
FACTOR_BANDS = [("low", 15, 35), ("medium", 36, 54), ("high", 55, 75)]
SUBSCALE_BANDS = [("low", 3, 6), ("medium", 7, 11), ("high", 12, 15)]
NORM_SOURCE = (
    "Katta beshlik paketi (2026-10-02): omil 15–35/36–54/55–75, birlamchi omil "
    "3–6/7–11/12–15. Normativ namuna va populyatsiya ko'rsatilmagan."
)


def item_code(number: int) -> str:
    return f"q{number:02d}"


def subscale_items(factor_index: int, block_index: int) -> list[int]:
    """Item numbers (1-based) of subscale `block_index` (0..4) in factor `factor_index`."""
    first = 15 * block_index + factor_index + 1
    return [first, first + 5, first + 10]


def factor_items(factor_index: int) -> list[int]:
    return sorted(
        number for block in range(5) for number in subscale_items(factor_index, block)
    )


_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "’", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "o‘", "қ": "q", "ғ": "g‘", "ҳ": "h",
}  # fmt: skip
_VOWELS = set("аеёиоуўэюяaeiou")


def transliterate(text: str) -> str:
    """Uzbek Cyrillic -> Latin (2023 alphabet rules for е and ц). Needs human review."""
    out: list[str] = []
    for index, char in enumerate(text):
        lower = char.lower()
        previous = text[index - 1].lower() if index else ""
        if lower == "е":
            word_start = not previous.isalpha() or previous in "ъь"
            latin = "ye" if word_start or previous in _VOWELS else "e"
        elif lower == "ц":
            latin = "ts" if previous in _VOWELS else "s"
        elif lower in _CYRILLIC_TO_LATIN:
            latin = _CYRILLIC_TO_LATIN[lower]
        else:
            out.append(char)
            continue
        if char != lower and latin:
            following = text[index + 1] if index + 1 < len(text) else ""
            all_caps = following.isupper()
            latin = latin.upper() if all_caps else latin[0].upper() + latin[1:]
        out.append(latin)
    return "".join(out)


def _i18n(cyrillic: str) -> dict[str, str]:
    return {"uz-Latn": transliterate(cyrillic), "uz-Cyrl": cyrillic}


def _bands(spec: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
    return [
        {
            "band_code": code,
            "lower_bound": str(lower),
            "lower_inclusive": True,
            "upper_bound": str(upper),
            "upper_inclusive": True,
        }
        for code, lower, upper in spec
    ]


def _scale(
    code: str, kind: str, label: str, numbers: list[int], bands: list
) -> dict[str, Any]:
    count = len(numbers)
    return {
        "scale_code": code,
        "scale_kind": kind,
        "label_i18n": _i18n(label),
        "item_codes": [item_code(number) for number in numbers],
        "unit_code": "raw_point",
        "theoretical_min": str(count * 1),
        "theoretical_max": str(count * 5),
        "display_decimals": 0,
        # The source gives no rule for missing answers, so every item is required.
        "aggregation": {"op": "sum", "min_answered": count, "max_missing": 0},
        "norm": {
            "norm_code": f"{code}_source_levels",
            "norm_kind": "threshold_bands",
            "source_reference": NORM_SOURCE,
            "bands": _bands(bands),
        },
    }


def build_snapshot(texts: dict[str, Any] | None = None) -> dict[str, Any]:
    """The scoring snapshot. Without `texts`, items carry no statements (tests, CI)."""
    texts = texts or {}
    statements = texts.get("items", {})
    items = []
    for number in range(1, ITEM_COUNT + 1):
        item: dict[str, Any] = {
            "item_code": item_code(number),
            "item_type": "single_choice",
            "required": True,
            "options": [
                {
                    "option_code": answer,
                    "ordinal_position": position,
                    "score_value": str(points),
                    "label_i18n": {
                        "uz-Latn": ANSWER_LABELS[answer][0],
                        "uz-Cyrl": ANSWER_LABELS[answer][1],
                    },
                }
                for position, (answer, points) in enumerate(ANSWER_POINTS.items(), 1)
            ],
            "reverse_scoring": {"mode": "none"},
        }
        pair = statements.get(str(number))
        if pair:
            item["prompt_i18n"] = {
                "uz-Latn": f"Chap: {transliterate(pair['left'])} | "
                f"O‘ng: {transliterate(pair['right'])}",
                "uz-Cyrl": f"Чап: {pair['left']} | Ўнг: {pair['right']}",
            }
        items.append(item)

    scales = []
    for factor_index, (code, label, subscales) in enumerate(FACTORS):
        scales.append(
            _scale(code, "factor", label, factor_items(factor_index), FACTOR_BANDS)
        )
        for block_index, (sub_code, sub_label) in enumerate(subscales):
            scales.append(
                _scale(
                    sub_code,
                    "subscale",
                    sub_label,
                    subscale_items(factor_index, block_index),
                    SUBSCALE_BANDS,
                )
            )

    interpretations = []
    for code, levels in texts.get("interpretations", {}).items():
        for priority, band in enumerate(("high", "low"), 1):
            if not levels.get(band):
                continue
            interpretations.append(
                {
                    "rule_code": f"{code}_{band}",
                    "scale_code": code,
                    "priority": priority,
                    "when": {
                        "op": "eq",
                        "left": {"op": "ref", "kind": "norm_band_code", "code": code},
                        "right": {"op": "const", "value": band},
                    },
                    "interpretation_code": f"{code}_{band}_text",
                    "text_i18n": _i18n(levels[band]),
                }
            )
    return {
        "methodology_code": METHODOLOGY_CODE,
        "version_code": VERSION_CODE,
        "items": items,
        "scales": scales,
        "interpretations": interpretations,
    }


def build_version_payload(texts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Body for POST /methodologies/{id}/versions."""
    return {
        "version_code": VERSION_CODE,
        "default_locale": "uz-Latn",
        "supported_locales": ["uz-Latn", "uz-Cyrl"],
        "target_population": {"adults_only": True, "min_age": 18},
        "estimated_minutes": 20,
        "disclaimer_i18n": {
            "uz-Latn": "Bu natija tibbiy tashxis emas.",
            "uz-Cyrl": "Бу натижа тиббий ташхис эмас.",
        },
        "snapshot": build_snapshot(texts),
    }


def points_for(answers: dict[str, str], numbers: list[int]) -> int:
    """Hand-computed reference score: sum of ANSWER_POINTS (used by tests)."""
    return sum(ANSWER_POINTS[answers[item_code(number)]] for number in numbers)


def parse_source_text(text: str) -> dict[str, Any]:
    """Statements, instruction and factor interpretations from the source as text.

    Expects the layout produced by scripts/extract_big_five_texts.py: table cells
    joined with ' | '.
    """
    pairs = {}
    pattern = re.compile(
        r"(?m)^(\d{1,2}) \| (.+?) \| -2 \| -1 \| 0 \| 1 \| 2 \| (.+?) \|", re.S
    )
    for match in pattern.finditer(text):
        number = int(match.group(1))
        if 1 <= number <= ITEM_COUNT and str(number) not in pairs:
            pairs[str(number)] = {
                "left": _clean(match.group(2)),
                "right": _clean(match.group(3)),
            }
    instruction = re.search(r"Йўриқнома:(.+?)\n1 \|", text, re.S)
    headings = [
        "БИРИНЧИ ОМИЛ",
        "ИККИНЧИ ОМИЛ",
        "УЧИНЧИ ОМИЛ",
        "ТЎРТИНЧИ ОМИЛ",
        "БЕШИНЧИ ОМИЛ",
    ]
    interpretations = {}
    for index, heading in enumerate(headings):
        start = text.find(heading)
        end = text.find(headings[index + 1]) if index + 1 < len(headings) else len(text)
        if start < 0:
            continue
        # Skip the heading and the factor title line; the rest is "high | low |".
        body = text[start:end].split("\n", 2)[2]
        high, _, low = body.partition(" | ")
        interpretations[FACTORS[index][0]] = {
            "high": _clean(high),
            "low": _clean(low.rstrip(" |\n")),
        }
    return {
        "instruction": _clean(instruction.group(1)) if instruction else "",
        "items": pairs,
        "interpretations": interpretations,
    }


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" |")
