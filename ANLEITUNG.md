# Vinted Zentrale – Ablauf

## Für dich

1. **Fotos** pro Paar machen (Seitenansicht, Größenetikett/Innensohle, Marke, Laufsohle, Mängel) und unsortiert in `0_input_foto` legen.
2. **Claude sagen:** „Neue Fotos sind in 0_input_foto, bitte analysieren.“
3. **Zentrale öffnen:** Doppelklick auf `Freigabe starten.bat` → http://127.0.0.1:8765
   - Ansicht **Inserate**: Fragen im roten Kasten per Knopf beantworten, Fotos sortieren.
   - Ansicht **Preise**: Preise festlegen (Vorschlag oder Vinted-Empfehlung übernehmen oder selbst tippen).
     „Vinted-Preise abfragen“ liest Vinteds Empfehlung aus (speichert nichts bei Vinted).
   - **Freigeben** → **In Vinted ausfüllen** → im Vinted-Chrome prüfen und selbst „Save draft“/„Upload“ klicken.
4. **Vinted-Chrome:** `Vinted Login.bat` (oder Knopf oben rechts in der Zentrale). Einmal selbst einloggen, Fenster offen lassen.
5. **Statistik:** Knopf „Statistik abrufen“ (oben rechts oder in der Ansicht **Statistik**) liest Aufrufe und Favoriten
   aller Vinted-Inserate (nur lesen) und speichert jeden Abruf in `statistik.json`. Verkaufte Artikel werden dabei automatisch
   auf „Verkauft“ gesetzt.

Inseratstexte: Titel Englisch, Beschreibung immer Englisch + Deutsch.

Tempo: lieber 3–6 Paare pro Tag einstellen (Vinted bevorzugt frische Inserate, und es wirkt weniger automatisiert).

## Für Claude (technisch)

- Neue Fotos finden + Kontaktbogen: `.venv\Scripts\python.exe werkzeuge\kontaktbogen.py` → `analyse\_kontakt_*.jpg` ansehen, Paare bilden,
  Fotos nach `schuhe\<NN_name>\` **kopieren** (Nummerierung fortsetzen, Originale bleiben in `0_input_foto`).
- Analyse: gespeicherter Workflow `vinted-analyse` (`.claude\workflows\vinted-analyse.js`), args = `[{ordner, fotos:[...]}]`.
  Schreibt `analyse\<ordner>.json` im Format der Zentrale (englischer Text, Fragen mit Textersetzungen, `preis_vorschlag`; `preis` bleibt leer).
- Prüfen: `werkzeuge\pruefe_inserat.py <datei.json>` · Übernehmen: `werkzeuge\uebernehmen.py` (überschreibt keine bearbeiteten Inserate).
- `inserate.json` nie aus einem alten Stand komplett überschreiben – nur per `vinted.setze_felder` / `uebernehmen.py` (die Zentrale kann parallel laufen).
- Upload-Befehle (`ausfuellen`, `hochladen`, `preise`) laufen über den Vinted-Chrome (CDP-Port 9222) und speichern bei Vinted nie selbst.
