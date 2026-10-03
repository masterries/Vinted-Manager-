# Vinted Zentrale – Ablauf

## Für dich

1. **Fotos** pro Paar machen (Seitenansicht, Größenetikett/Innensohle, Marke, Laufsohle, Mängel) und unsortiert in `0_input_photos` legen.
2. **Claude sagen:** „Neue Fotos sind in 0_input_photos, bitte analysieren.“
3. **Zentrale öffnen:** Doppelklick auf `Start Hub.bat` → http://127.0.0.1:8765
   - Ansicht **Inserate**: Fragen im roten Kasten per Knopf beantworten, Fotos sortieren.
   - Ansicht **Preise**: Preise festlegen (Vorschlag oder Vinted-Empfehlung übernehmen oder selbst tippen).
     „Vinted-Preise abfragen“ liest Vinteds Empfehlung aus (speichert nichts bei Vinted).
   - **Freigeben** → **In Vinted ausfüllen** → im Vinted-Chrome prüfen und selbst „Save draft“/„Upload“ klicken.
4. **Vinted-Chrome:** `Vinted Login.bat` (oder Knopf oben rechts in der Zentrale). Einmal selbst einloggen, Fenster offen lassen.
5. **Statistik:** Knopf „Statistik abrufen“ (oben rechts oder in der Ansicht **Statistik**) liest Aufrufe und Favoriten
   aller Vinted-Inserate (nur lesen) und speichert jeden Abruf in `data\stats.json`. Verkaufte Artikel werden dabei automatisch
   auf „Verkauft“ gesetzt.

Inseratstexte: Titel Englisch, Beschreibung immer Englisch + Deutsch.

Tempo: lieber 3–6 Paare pro Tag einstellen (Vinted bevorzugt frische Inserate, und es wirkt weniger automatisiert).

## Für Claude (technisch)

- Neue Fotos finden + Kontaktbogen: `.venv\Scripts\python.exe tools\contact_sheet.py` → `data\analysis\_contact_*.jpg` ansehen, Paare bilden,
  Fotos nach `data\items\<NN_name>\` **kopieren** (Nummerierung fortsetzen, Originale bleiben in `0_input_photos`).
- Analyse: gespeicherter Workflow `vinted-analysis` (`.claude\workflows\vinted-analysis.js`), args = `[{folder, photos:[...]}]`.
  Schreibt `data\analysis\<folder>.json` im Format der Zentrale (englischer Text, Fragen mit Textersetzungen, `suggested_price`; `price` bleibt leer).
- Prüfen: `tools\check_listing.py <datei.json>` · Übernehmen: `tools\import_listings.py` (überschreibt keine bearbeiteten Inserate).
- `data\listings.json` nie aus einem alten Stand komplett überschreiben – nur per `vinted_hub.core.update_fields` / `import_listings.py` (die Zentrale kann parallel laufen).
- Upload-Befehle (`python -m vinted_hub fill`, `fill-approved`, `prices`) laufen über den Vinted-Chrome (CDP-Port 9222) und speichern bei Vinted nie selbst.
- Code und Daten sind Englisch (z. B. Status `new`/`approved`/`draft`/`sold`), die Oberfläche Deutsch – Zuordnung in `CLAUDE.md`.
