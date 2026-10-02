"""Extract the Katta beshlik statements and interpretations from the source RTF.

The texts are licensed content: the output goes to methodologies/private/ (gitignored)
and is merged into the snapshot only when building a version locally.

    python scripts/extract_big_five_texts.py "КАТТА БЕШЛИК МЕТОДИКА.rtf"
    python scripts/extract_big_five_texts.py source.rtf --payload version.json

Exit code 0 means all 75 statement pairs and all 5 factor interpretations were found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodologies.big_five import (  # noqa: E402
    FACTORS,
    ITEM_COUNT,
    build_version_payload,
    parse_source_text,
)

# Groups whose content is not document text (font tables, styles, drawings, fields...).
SKIPPED_DESTINATIONS = {
    "fonttbl", "colortbl", "stylesheet", "info", "listtable", "listoverridetable",
    "rsidtbl", "latentstyles", "themedata", "colorschememapping", "datastore",
    "xmlnstbl", "pgptbl", "mmathPr", "shp", "footerl", "footerr", "ftnsep", "ftnsepc",
    "aftnsep", "aftnsepc", "fldinst", "defchp", "defpap", "xmlopen", "factoidname",
    "xmlattr",
} | {f"pnseclvl{level}" for level in range(1, 10)}  # fmt: skip
CONTROL_WORD = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?")


def rtf_to_text(source: str, codepage: str = "cp1251") -> str:
    """Plain text of an RTF document; table cells are joined with ' | '."""
    out: list[str] = []
    stack: list[bool] = []
    skip = False
    i, length = 0, len(source)
    while i < length:
        char = source[i]
        if char == "{":
            stack.append(skip)
            i += 1
            word = CONTROL_WORD.match(source, i)
            if source.startswith("\\*", i) or (
                word and word.group(1) in SKIPPED_DESTINATIONS
            ):
                skip = True
            continue
        if char == "}":
            skip = stack.pop() if stack else False
            i += 1
            continue
        if char in "\r\n":
            i += 1
            continue
        if char != "\\":
            if not skip:
                out.append(char)
            i += 1
            continue
        following = source[i + 1]
        if following == "'":
            if not skip:
                hex_code = source[i + 2 : i + 4]  # noqa: E203 (black slice style)
                out.append(bytes([int(hex_code, 16)]).decode(codepage))
            i += 4
            continue
        if following in "\\{}~":
            if not skip:
                out.append(" " if following == "~" else following)
            i += 2
            continue
        word = CONTROL_WORD.match(source, i)
        if not word:
            i += 2
            continue
        name, argument = word.group(1), word.group(2)
        i = word.end()
        if skip:
            continue
        if name == "u":
            out.append(chr(int(argument) % 65536))
            # Skip the ANSI fallback character; the RTF may wrap the line before it.
            while source[i] in "\r\n":
                i += 1
            i += 4 if source.startswith("\\'", i) else 1
        elif name in ("par", "line", "row"):
            out.append("\n")
        elif name == "cell":
            out.append(" | ")
        elif name == "tab":
            out.append("\t")
        elif name == "endash":
            out.append("–")
        elif name == "emdash":
            out.append("—")
    text = re.sub(r"[ \t]+", " ", "".join(out))
    return re.sub(r"\n\s*\n+", "\n", text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rtf", type=Path)
    parser.add_argument(
        "--out", type=Path, default=ROOT / "methodologies/private/big_five_texts.json"
    )
    parser.add_argument("--payload", type=Path, help="also write the version body")
    args = parser.parse_args()

    texts = parse_source_text(rtf_to_text(args.rtf.read_bytes().decode("latin-1")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(texts, ensure_ascii=False, indent=2), "utf-8")
    if args.payload:
        args.payload.write_text(
            json.dumps(build_version_payload(texts), ensure_ascii=False, indent=2),
            "utf-8",
        )

    missing_items = [
        n for n in range(1, ITEM_COUNT + 1) if str(n) not in texts["items"]
    ]
    missing_factors = [
        code for code, _label, _subs in FACTORS if code not in texts["interpretations"]
    ]
    print(
        f"statements: {len(texts['items'])}/{ITEM_COUNT}, "
        f"interpretations: {len(texts['interpretations'])}/{len(FACTORS)} -> {args.out}"
    )
    if missing_items or missing_factors:
        print(f"missing items {missing_items}, missing factors {missing_factors}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
