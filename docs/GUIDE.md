# Vinted Zentrale – Ablauf

English version: [GUIDE.en.md](GUIDE.en.md)

## Für dich

1. **Fotos** pro Paar machen (Seitenansicht, Größenetikett/Innensohle, Marke, Laufsohle, Mängel) und unsortiert in `0_input_photos` legen.
2. **Claude sagen:** „Neue Fotos sind in 0_input_photos, bitte analysieren.“
3. **Zentrale öffnen:** Doppelklick auf `Start Hub.bat` → http://127.0.0.1:8765
   - Ansicht **Inserate**: Fragen im roten Kasten **Fehlt noch** per Knopf beantworten, Fotos sortieren.
   - Ansicht **Preise**: Preise festlegen (Vorschlag oder Vinted-Empfehlung übernehmen oder selbst tippen).
     „Vinted-Preise abfragen“ liest Vinteds Empfehlung aus (speichert nichts bei Vinted).
   - **Freigeben** → **In Vinted ausfüllen** (auch die Paketgröße: Medium, bei sehr großen Schuhen Large) → im Vinted-Chrome
     prüfen und selbst „Save draft“/„Upload“ klicken. Danach erkennt die Zentrale selbst, ob das Inserat online oder ein Entwurf ist.
4. **Vinted-Chrome:** `Vinted Login.bat` (oder Knopf „Öffnen“ oben rechts in der Zentrale). Einmal selbst einloggen, Fenster offen lassen.
5. **Statistik:** Knopf „Statistik abrufen“ (oben rechts oder in der Ansicht **Statistik**) liest Aufrufe und Favoriten
   aller Vinted-Inserate (nur lesen) und speichert jeden Abruf in `data\stats.json`. Verkaufte Artikel werden dabei automatisch
   auf „Verkauft“ gesetzt.

Tempo: lieber 3–6 Paare pro Tag einstellen (Vinted bevorzugt frische Inserate, und es wirkt weniger automatisiert).

## Einstellungen

Knopf **Einstellungen** in der Kopfzeile der Zentrale. Jede Einstellung hat zwei Werte, Deutsch oder Englisch:

| Einstellung | Was sie bewirkt |
|---|---|
| **Sprache der Oberfläche** | Sprache der Zentrale (Knöpfe, Meldungen, Protokolle) und der Texte, die Claude bei **neuen** Analysen für dich schreibt: Fragen, Antwort-Knöpfe, Hinweise, Preisbegründung. |
| **Sprache der Titel** | In welcher Sprache Claude die Titel neuer Inserate schreibt (Englisch z. B. „… Size 39“, Deutsch „… Gr. 39“). |
| **Sprache der Beschreibung** | In welcher Sprache Claude die Beschreibung neuer Inserate schreibt – immer nur eine Sprache, nie zweisprachig. |

- Die Wahl wird in `data\settings.json` gespeichert (nur auf deinem Rechner). Ohne eigene Wahl gilt überall Englisch.
- Bestehende Inserate ändern sich dabei **nicht**. Der Dialog zeigt, wie viele noch nicht eingestellte Inserate (zu prüfen,
  zurückgestellt, freigegeben) in einer anderen Sprache geschrieben sind. Die Zentrale übersetzt nicht selbst – wenn du sie
  umgeschrieben haben willst, sag es Claude, z. B. „Bitte die offenen Inserate auf Deutsch umschreiben.“
- Fragen und Hinweise in bestehenden Inseraten bleiben in der Sprache, in der sie geschrieben wurden.

## Für Claude (technisch)

- Neue Fotos finden + Kontaktbogen: `.venv\Scripts\python.exe tools\contact_sheet.py` → `data\analysis\_contact_*.jpg` ansehen, Paare bilden,
  Fotos nach `data\items\<NN_name>\` **kopieren** (Nummerierung fortsetzen, Originale bleiben in `0_input_photos`).
- Einstellungen lesen: `.venv\Scripts\python.exe -m vinted_hub settings` (eine JSON-Zeile; ändern mit `settings set key=value`).
- Analyse: gespeicherter Workflow `vinted-analysis` (`.claude\workflows\vinted-analysis.js`),
  args = `{settings: <JSON von oben>, items: [{folder, photos:[...]}]}`. Schreibt `data\analysis\<folder>.json` im Format der
  Zentrale (Titel/Beschreibung in den eingestellten Sprachen, Beschreibung nur in einer Sprache, Felder `title_language` /
  `description_language`, Fragen mit Textersetzungen, `suggested_price`; `price` bleibt leer).
- Prüfen: `tools\check_listing.py <datei.json>` · Übernehmen: `tools\import_listings.py` (überschreibt keine bearbeiteten Inserate).
- `data\listings.json` nie aus einem alten Stand komplett überschreiben – nur per `vinted_hub.core.update_fields` / `import_listings.py` (die Zentrale kann parallel laufen).
- Upload-Befehle (`python -m vinted_hub fill`, `fill-approved`, `prices`) laufen über den Vinted-Chrome (CDP-Port 9222) und speichern bei Vinted nie selbst.
- Code und Daten sind Englisch (z. B. Status `new`/`approved`/`draft`/`sold`), die Oberfläche zweisprachig (Englisch im Code,
  Deutsch in den `DE`-Wörterbüchern) – Zuordnung und Umschreib-Ablauf in `CLAUDE.md`.
