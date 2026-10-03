"""Übernimmt geprüfte Analyse-Ergebnisse (analyse/<ordner>.json) in inserate.json.

Aufruf:  python werkzeuge/uebernehmen.py [ordner ...]     (ohne Angabe: alle analyse/*.json)
- Jede Datei muss das Prüfwerkzeug bestehen, sonst wird sie übersprungen.
- Neue Ordner werden angehängt. Bestehende Inserate werden NICHT überschrieben,
  außer mit --ersetzen und nur, solange sie noch "neu" sind und keine Frage beantwortet ist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vinted  # noqa: E402
from pruefe_inserat import pruefe  # noqa: E402

AUS = vinted.BASIS / "analyse"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ersetzen = "--ersetzen" in sys.argv
    dateien = [AUS / f"{o}.json" for o in args] if args else sorted(AUS.glob("[!_]*.json"))
    config = vinted.lade_config()
    inserate = vinted.lese_inserate(config)
    nach_ordner = {i["ordner"]: n for n, i in enumerate(inserate)}
    neu, ersetzt, uebersprungen = [], [], []
    for datei in dateien:
        inserat = json.loads(datei.read_text(encoding="utf-8-sig"))
        probleme = pruefe(inserat)
        if probleme:
            uebersprungen.append(f"{datei.name}: {probleme[0]}")
            continue
        inserat.setdefault("status", "neu")
        inserat.setdefault("verlauf", [])
        o = inserat["ordner"]
        if o in nach_ordner:
            alt = inserate[nach_ordner[o]]
            unberuehrt = alt.get("status") == "neu" and not any(q.get("antwort") for q in alt.get("fragen") or [])
            if ersetzen and unberuehrt:
                inserate[nach_ordner[o]] = inserat
                ersetzt.append(o)
            else:
                uebersprungen.append(f"{o}: gibt es schon (mit --ersetzen nur, solange unbearbeitet)")
            continue
        inserate.append(inserat)
        neu.append(o)
    vinted.schreibe_inserate(config, inserate)
    print("Neu:", ", ".join(neu) or "-")
    if ersetzt:
        print("Ersetzt:", ", ".join(ersetzt))
    for u in uebersprungen:
        print("Übersprungen:", u)


if __name__ == "__main__":
    main()
