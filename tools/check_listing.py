"""Checks a generated listing (JSON file with one object or a list) against the hub's format.

Usage:   python tools/check_listing.py listing.json
Checks:
  - required fields and allowed values (condition, package)
  - every question: every option finds its first text snippet in title/description
  - every option applied on its own: no double spaces, no " ," / " ." leftovers
  - layout: the description may separate its blocks with ONE blank line (looks better on Vinted), but no
    double blank lines, no blank line at the start/end, no line of only spaces; the title is one line
  - length: description at most DESCRIPTION_MAX characters while not on Vinted yet (short and readable)
  - all questions answered with option 1: no "[?" remains in title/description
  - no "[?" without a matching question
  - language (only while not on Vinted yet: status new / on_hold / approved): title and description are
    written in the listing's own "title_language" / "description_language" (fallback: the settings),
    never bilingual (no line that is only a language name with decoration: "— Deutsch —", "=== English ===",
    "Deutsch:", "🇩🇪 Deutsch" ...);
    markers "[? …]" in the listing's language: "[?]" always, otherwise en "[? please …]" / de "[? bitte …]";
    "en": no typical German words/labels (Größe, Zustand, Absatzhöhe, Glattleder, Karton, "Gr. 39" / "Gr. [?]" ...);
    "de" description: no typical English labels/phrases ("Size:", "Heel height:", "approx.", leather, with ...);
    "de" title: only structural English words count ("Size 39" / "Size [?]", Women's/Men's/Ladies, with, and) -
    colour/material words are often part of a model name ("Smooth Leather", "Triple White") and stay allowed;
    the same rule applies to the text after every single option and after all first options
    (problems the listing itself already has are not repeated)
  - "title_language" / "description_language", if present, are "en" or "de"
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
DESCRIPTION_MAX = 700  # short descriptions read better on Vinted (Vinted's own limit is 2000)

# --- language rule ---
LANGUAGES = core.SETTINGS_CHOICES["description_language"]  # ["en", "de"]
STILL_LOCAL = ("new", "on_hold", "approved")  # not on Vinted yet: texts can still be rewritten
# A block in a second language is never allowed: any line that is only a language name with decoration
# ("— Deutsch —", "-- English --", "=== Deutsch ===", "Deutsch:", "🇩🇪 Deutsch", "–– DE ––")
BILINGUAL_SEPARATOR = re.compile(r"^[^\w\n]*(Deutsch|German|Englisch|English|DE|EN)[^\w\n]*$", re.I | re.M)
# Markers: "[?]" in both languages, otherwise only the wording of the listing's language
MARKER = re.compile(r"\[\?([^\]\n]*)\]")
MARKER_OK = {"en": re.compile(r"^\s*$|^\s*(please|confirm|check)\b", re.I),     # "[? please confirm]"
             "de": re.compile(r"^\s*$|^\s*(bitte|prüfen|bestätigen)\b", re.I)}  # "[? bitte bestätigen]"
MARKER_EXAMPLE = {"en": "[? please confirm]", "de": "[? bitte bestätigen]"}
GERMAN_MARKER = re.compile(r"\[\?\s*(bitte|prüfen|bestätigen)", re.I)   # "[? bitte bestätigen, sonst Zeile löschen]"
ENGLISH_MARKER = re.compile(r"\[\?\s*(please|confirm|check)", re.I)     # "[? please confirm]"
# "Material:" is the same in both languages and therefore not listed
GERMAN_LABEL_LINE = re.compile(
    r"^\s*(Größe|Groesse|Zustand|Absatzhöhe|Absatz|Obermaterial|Innenmaterial|Futter|Innensohle|Innenlänge|Laufsohle|"
    r"Sohle|Schuhform|Form|Farbe|Marke|Mängel|Kleine Mängel|Hinweis|Passform|Maße|Länge|Breite|Versand|Zubehör|"
    r"Karton(/Etikett)?|Etikett)"
    r"\s*(\([^)\n]*\))?\s*:", re.I | re.M)
GERMAN_WORDS = re.compile(
    r"\b(Größe|Groesse|Zustand|Absatzhöhe|Absatz|Blockabsatz|Keilabsatz|Stilettoabsatz|Obermaterial|Innensohle|"
    r"Laufsohlen?|Sohlen?|geschätzt|getragen|ungetragen|Gebrauchsspuren|neuwertig|sehr gut|Schuhe|Stiefel|"
    r"Stiefeletten|Sandaletten|Sandalen|\w*leder|Damen|Farbe|Mängel|Versand|vermutlich|anprobiert|"
    r"Spuren|Karton|Originalkarton|Etikett|siehe|nur|nie|keine|kurz|"
    r"Schuhform|Futter|(schwarz|weiß|weiss|braun|grau|grün|blau|gelb|silber)(e|en|er|es)?|"
    r"pink(e|en|es)|(rot|golden|silbern)(e|en|er|es)|bitte|mit|ohne|und)\b|\bGr\.\s*(EU\s*)?(\d|\[\?)", re.I)
ENGLISH_LABEL_LINE = re.compile(
    r"^\s*(Size|Heel height|Heel|Condition|Shape|Upper|Lining|Insole|Insole length|Outsole|Sole|Colou?r|Brand|"
    r"Flaws|Small flaws|Fit|Length|Width|Platform|Box(/tags)?|Tags)\s*(\([^)\n]*\))?\s*:", re.I | re.M)
ENGLISH_WORDS = re.compile(
    r"\b(please confirm|estimated|approximately|never worn|barely worn|worn|very good condition|good condition|"
    r"insole length|heel height|with tags|without tags|size|leather|suede|faux|probably|tried on|signs of wear|"
    r"outsoles?|insole|upper|lining|original box|comes|with|and|the)\b|\bapprox\.", re.I)
# German title: only structural English words. Colour/material words are often part of a model or colourway
# name ("Smooth Leather", "Triple White", "Black/White") and stay allowed; whether the colour words are natural
# German is checked by the reviewer agent.
ENGLISH_TITLE_WORDS = re.compile(r"\bSize\s*:?\s*(EU\s*)?(\d|\[\?)|\b(Women['’]?s|Men['’]?s|Ladies|with|and)\b", re.I)
_settings_cache: dict = {}


def settings() -> dict:
    if not _settings_cache:
        _settings_cache.update(core.current_settings(core.load_config()))
    return _settings_cache


def _plain(text: str, listing: dict, also_ignore: tuple = ()) -> str:
    """Text without hashtags, quoted prints (e.g. insole stamp "Echt Leder" or a model name in „…“),
    the brand name and the model name (analysis.model) - these may be in any language. `also_ignore`:
    more brand names (e.g. the original brand after a "No brand" / "Other brand" option changed the brand field)."""
    text = re.sub(r"#\S+", " ", text or "")
    text = re.sub(r'"[^"\n]*"|„[^“”"\n]*[“”"]|“[^”\n]*”', " ", text)
    model = (listing.get("analysis") or {}).get("model") if isinstance(listing.get("analysis"), dict) else None
    for brand in (listing.get("brand"), model) + tuple(also_ignore):
        brand = str(brand or "").strip()
        if len(brand) >= 2:
            text = re.sub(re.escape(brand), " ", text, flags=re.I)
    return text


def _first(pattern, text: str):
    m = pattern.search(text)
    return m.group(0).strip() if m else None


def language_errors(listing: dict, also_ignore: tuple = ()) -> list[str]:
    """Problems with the language fields and with the language of title and description."""
    p = []
    lang = {}
    for field, key in (("title", "title_language"), ("description", "description_language")):
        value = listing.get(key)
        if value is None:
            lang[field] = settings()[key]
        elif value in LANGUAGES:
            lang[field] = value
        else:
            p.append(f"{key} {value!r} ungültig (erlaubt: {', '.join(LANGUAGES)})")
    if listing.get("status", "new") not in STILL_LOCAL:
        return p
    description = listing.get("description") or ""
    separator = _first(BILINGUAL_SEPARATOR, description)
    if separator:
        p.append(f"Beschreibung zweisprachig (Trennzeile {separator!r}), erlaubt ist genau eine Sprache")
    names = {"title": "Titel", "description": "Beschreibung"}
    for field, language in lang.items():
        text = listing.get(field) or ""
        plain = _plain(text, listing, also_ignore)
        if language == "en":
            found = (_first(GERMAN_MARKER, text) or _first(GERMAN_LABEL_LINE, plain) or _first(GERMAN_WORDS, plain))
            if found:
                p.append(f"{names[field]} soll Englisch sein ({field}_language en), deutscher Text gefunden: {found!r}")
        else:
            found = (_first(ENGLISH_MARKER, text) or _first(ENGLISH_LABEL_LINE, plain)
                     or _first(ENGLISH_TITLE_WORDS if field == "title" else ENGLISH_WORDS, plain))
            if found:
                p.append(f"{names[field]} soll Deutsch sein ({field}_language de), englischer Text gefunden: {found!r}"
                         + (" (englischer Modellname? dann in „…“ setzen)" if field == "description" else ""))
        for m in MARKER.finditer(text):  # a marker already named in the message above is not reported twice
            if not MARKER_OK[language].search(m.group(1)) and not (found and found in m.group(0)):
                p.append(f"{names[field]}: Marker {m.group(0)!r} passt nicht zu {field}_language {language} "
                         f"(erlaubt: '[?]' oder {MARKER_EXAMPLE[language]!r})")
    return p


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
        if f == "title":
            if "\n" in t:
                problems.append("title: Zeilenumbruch im Titel")
            continue
        # description: single blank lines between blocks are fine (looks better on Vinted)
        if re.search(r"\n[ \t]*\n[ \t]*\n", t):
            problems.append(f"{f}: doppelte Leerzeile")
        if re.search(r"^[ \t]*\n|\n[ \t]*$", t):
            problems.append(f"{f}: Leerzeile am Anfang oder Ende")
        if re.search(r"(^|\n)[ \t]+(\n|$)", t):
            problems.append(f"{f}: Zeile nur aus Leerzeichen")
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
    elif listing.get("status", "new") in STILL_LOCAL and len(listing.get("description") or "") > DESCRIPTION_MAX:
        p.append(f"{name}: Beschreibung zu lang ({len(listing['description'])} Zeichen, max. {DESCRIPTION_MAX}) – kürzer fassen")
    own_language = language_errors(listing)
    p += [f"{name}: {x}" for x in own_language]
    seen_language = set(own_language)  # language problems already reported (not repeated for the options)
    brand = (listing.get("brand"),)    # the original brand stays ignored after a brand option
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
            # the replacement texts must be in the listing's language too
            new = [x for x in language_errors(test, brand) if x not in own_language]
            p += [f"{name}/{q.get('id')}/{opt.get('label')}: {x}" for x in new]
            seen_language.update(new)
    test = copy.deepcopy(listing)
    for q in questions:
        if q.get("options"):
            apply_option(test, q, q["options"][0])
    p += [f"{name}: nach allen Antworten: {x}" for x in language_errors(test, brand) if x not in seen_language]
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
