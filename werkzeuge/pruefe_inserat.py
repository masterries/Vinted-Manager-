"""Prüft ein erzeugtes Inserat (JSON-Datei mit einem Objekt oder einer Liste) auf das Format der Zentrale.

Aufruf:  python werkzeuge/pruefe_inserat.py inserat.json
Prüft:
  - Pflichtfelder und erlaubte Werte (Zustand, Paket)
  - jede Frage: jede Option findet ihre erste Textstelle in Titel/Beschreibung
  - jede Option einzeln angewendet: keine doppelten Leerzeichen, keine " ," / " ." Reste
  - alle Fragen mit Option 1 beantwortet: kein "[?" bleibt in Titel/Beschreibung
  - kein "[?" ohne zugehörige Frage
Exit-Code 0 = alles in Ordnung, sonst 1 (mit Liste der Probleme).
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vinted  # noqa: E402

TEXT = ("titel", "beschreibung")
PFLICHT = ["ordner", "titel", "beschreibung", "kategorie", "marke", "groesse", "zustand", "farbe", "paket"]
TESTWERT = {"groesse": "39"}


def wende_an(inserat: dict, frage: dict, opt: dict) -> list[str]:
    """Wendet eine Option an (wie freigabe.beantworte). Gibt nicht gefundene Pflicht-Textstellen zurück."""
    wert = TESTWERT.get(frage.get("feld") or frage.get("id"), "Testwert") if opt.get("eingabe") else ""
    fehlend = []
    for paar in opt.get("ersetzen") or []:
        alt, neu = paar[0], paar[1].replace("{wert}", wert)
        optional = len(paar) > 2 and paar[2]
        treffer = False
        for f in TEXT:
            if alt in (inserat.get(f) or ""):
                inserat[f] = inserat[f].replace(alt, neu)
                treffer = True
        if not treffer and not optional:
            fehlend.append(alt)
    for k, v in (opt.get("felder") or {}).items():
        inserat[k] = v.replace("{wert}", wert) if isinstance(v, str) else v
    return fehlend


def textfehler(inserat: dict) -> list[str]:
    probleme = []
    for f in TEXT:
        t = inserat.get(f) or ""
        for zeile in t.split("\n"):
            if "  " in zeile.strip():
                probleme.append(f"{f}: doppeltes Leerzeichen in {zeile.strip()[:70]!r}")
            if re.search(r"\s[,.;:]", zeile):
                probleme.append(f"{f}: Leerzeichen vor Satzzeichen in {zeile.strip()[:70]!r}")
        if re.search(r"\n\s*\n", t):
            probleme.append(f"{f}: leere Zeile")
    return probleme


def pruefe(inserat: dict) -> list[str]:
    p = []
    name = inserat.get("ordner", "?")
    for k in PFLICHT:
        if k not in inserat or inserat[k] in (None, ""):
            p.append(f"{name}: Feld {k} fehlt")
    if inserat.get("zustand") not in vinted.ZUSTAENDE:
        p.append(f"{name}: zustand {inserat.get('zustand')!r} nicht in {vinted.ZUSTAENDE}")
    if inserat.get("paket") not in vinted.PAKETE:
        p.append(f"{name}: paket {inserat.get('paket')!r} nicht in {vinted.PAKETE}")
    if len(inserat.get("beschreibung") or "") > 2000:
        p.append(f"{name}: Beschreibung länger als 2000 Zeichen (Vinted-Grenze)")
    zweisprachig = "de" in str(vinted.lade_config().get("sprache_inseratstext", ""))
    noch_lokal = inserat.get("status", "neu") in ("neu", "zurueckgestellt", "freigegeben")
    if zweisprachig and noch_lokal and "\n— Deutsch —\n" not in (inserat.get("beschreibung") or ""):
        p.append(f"{name}: Beschreibung nicht zweisprachig (Zeile '— Deutsch —' fehlt)")
    if len(inserat.get("titel") or "") > 70:
        p.append(f"{name}: Titel länger als 70 Zeichen")
    alle_fragen = inserat.get("fragen") or []
    fragen = [q for q in alle_fragen if not q.get("antwort")]  # beantwortete sind erledigt
    ids = [q.get("id") for q in alle_fragen]
    if len(ids) != len(set(ids)):
        p.append(f"{name}: doppelte Fragen-IDs {ids}")
    p += [f"{name}: {x}" for x in textfehler(inserat)]
    for q in fragen:
        if not q.get("optionen"):
            p.append(f"{name}/{q.get('id')}: keine Optionen")
        for opt in q.get("optionen") or []:
            test = copy.deepcopy(inserat)
            fehlend = wende_an(test, q, opt)
            if fehlend:
                p.append(f"{name}/{q.get('id')}/{opt.get('label')}: Textstelle nicht gefunden: {fehlend[0]!r}")
            p += [f"{name}/{q.get('id')}/{opt.get('label')}: {x}" for x in textfehler(test)]
    test = copy.deepcopy(inserat)
    for q in fragen:
        if q.get("optionen"):
            wende_an(test, q, q["optionen"][0])
    for f in TEXT:
        if "[?" in (test.get(f) or ""):
            rest = [z for z in test[f].split("\n") if "[?" in z]
            p.append(f"{name}: nach allen Antworten bleibt ein Platzhalter in {f}: {rest[0][:80]!r}")
    return p


def main() -> None:
    daten = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    inserate = daten if isinstance(daten, list) else [daten]
    probleme = [x for i in inserate for x in pruefe(i)]
    if probleme:
        print("PROBLEME:")
        print("\n".join(" - " + x for x in probleme))
        sys.exit(1)
    print(f"OK: {len(inserate)} Inserat(e) ohne Probleme")


if __name__ == "__main__":
    main()
