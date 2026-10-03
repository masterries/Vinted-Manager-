"""Checks a generated listing (JSON file with one object or a list) against the hub's format.

Usage:   python tools/check_listing.py listing.json
Checks:
  - required fields and allowed values (condition, package)
  - every question: every option finds its first text snippet in title/description
  - every option applied on its own: no double spaces, no " ," / " ." leftovers
  - all questions answered with option 1: no "[?" remains in title/description
  - no "[?" without a matching question
Exit code 0 = all fine, otherwise 1 (with a list of problems).
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_hub import core  # noqa: E402

TEXT = ("title", "description")
REQUIRED = ["folder", "title", "description", "category", "brand", "size", "condition", "color", "package"]
TEST_VALUE = {"size": "39"}


def apply_option(listing: dict, question: dict, opt: dict) -> list[str]:
    """Applies one option (like server.answer_question). Returns required text snippets that were not found."""
    value = TEST_VALUE.get(question.get("field") or question.get("id"), "TestValue") if opt.get("input") else ""
    missing = []
    for pair in opt.get("replace") or []:
        old, new = pair[0], pair[1].replace("{value}", value)
        optional = len(pair) > 2 and pair[2]
        hit = False
        for f in TEXT:
            if old in (listing.get(f) or ""):
                listing[f] = listing[f].replace(old, new)
                hit = True
        if not hit and not optional:
            missing.append(old)
    for k, v in (opt.get("fields") or {}).items():
        listing[k] = v.replace("{value}", value) if isinstance(v, str) else v
    return missing


def text_errors(listing: dict) -> list[str]:
    problems = []
    for f in TEXT:
        t = listing.get(f) or ""
        for line in t.split("\n"):
            if "  " in line.strip():
                problems.append(f"{f}: doppeltes Leerzeichen in {line.strip()[:70]!r}")
            if re.search(r"\s[,.;:]", line):
                problems.append(f"{f}: Leerzeichen vor Satzzeichen in {line.strip()[:70]!r}")
        if re.search(r"\n\s*\n", t):
            problems.append(f"{f}: leere Zeile")
    return problems


def check(listing: dict) -> list[str]:
    p = []
    name = listing.get("folder", "?")
    for k in REQUIRED:
        if k not in listing or listing[k] in (None, ""):
            p.append(f"{name}: Feld {k} fehlt")
    if listing.get("condition") not in core.CONDITIONS:
        p.append(f"{name}: condition {listing.get('condition')!r} nicht in {core.CONDITIONS}")
    if listing.get("package") not in core.PACKAGES:
        p.append(f"{name}: package {listing.get('package')!r} nicht in {core.PACKAGES}")
    if len(listing.get("description") or "") > 2000:
        p.append(f"{name}: Beschreibung länger als 2000 Zeichen (Vinted-Grenze)")
    bilingual = "de" in str(core.load_config().get("listing_language", ""))
    still_local = listing.get("status", "new") in ("new", "on_hold", "approved")
    if bilingual and still_local and "\n— Deutsch —\n" not in (listing.get("description") or ""):
        p.append(f"{name}: Beschreibung nicht zweisprachig (Zeile '— Deutsch —' fehlt)")
    if len(listing.get("title") or "") > 70:
        p.append(f"{name}: Titel länger als 70 Zeichen")
    all_questions = listing.get("questions") or []
    questions = [q for q in all_questions if not q.get("answer")]  # answered ones are done
    ids = [q.get("id") for q in all_questions]
    if len(ids) != len(set(ids)):
        p.append(f"{name}: doppelte Fragen-IDs {ids}")
    p += [f"{name}: {x}" for x in text_errors(listing)]
    for q in questions:
        if not q.get("options"):
            p.append(f"{name}/{q.get('id')}: keine Optionen")
        for opt in q.get("options") or []:
            test = copy.deepcopy(listing)
            missing = apply_option(test, q, opt)
            if missing:
                p.append(f"{name}/{q.get('id')}/{opt.get('label')}: Textstelle nicht gefunden: {missing[0]!r}")
            p += [f"{name}/{q.get('id')}/{opt.get('label')}: {x}" for x in text_errors(test)]
    test = copy.deepcopy(listing)
    for q in questions:
        if q.get("options"):
            apply_option(test, q, q["options"][0])
    for f in TEXT:
        if "[?" in (test.get(f) or ""):
            rest = [line for line in test[f].split("\n") if "[?" in line]
            p.append(f"{name}: nach allen Antworten bleibt ein Platzhalter in {f}: {rest[0][:80]!r}")
    return p


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    listings = data if isinstance(data, list) else [data]
    problems = [x for i in listings for x in check(i)]
    if problems:
        print("PROBLEME:")
        print("\n".join(" - " + x for x in problems))
        sys.exit(1)
    print(f"OK: {len(listings)} Inserat(e) ohne Probleme")


if __name__ == "__main__":
    main()
