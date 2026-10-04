# AGENTS.md

Die vollständige Arbeitsanweisung für KI-Agenten steht in **[CLAUDE.md](CLAUDE.md)** – bitte zuerst dort lesen.

Kurzfassung:
- Projekt: Verkaufs-Pipeline für private Schuhe auf vinted.lu (Fotos → Analyse → lokale „Zentrale“ → Vinted-Formular ausfüllen).
  Code im Paket `vinted_hub\` (`python -m vinted_hub serve|login|fill|fill-approved|prices|stats|explore|settings`), Werkzeuge in `tools\`.
- Mit dem Nutzer Deutsch sprechen. Code, Dateinamen und JSON-Daten sind Englisch.
- Oberfläche zweisprachig (Einstellung `ui_language`): Texte im Code auf Englisch, deutsche Übersetzung in `DE` in
  `vinted_hub\i18n.py` bzw. in `vinted_hub\web\js\i18n\de.<bereich>.js` – jeder neue sichtbare Text braucht beide Fassungen
  (Englisch in britischer Schreibweise; prüfen: `.venv\Scripts\python.exe tools\check_i18n.py`); gespeicherte Werte bleiben
  Englisch (Zuordnung in CLAUDE.md, „Namen (Code ↔ Oberfläche)“).
  Ausnahme: Die Werkzeuge in `tools\` (Prüfwerkzeug, Import, Kontaktbogen) melden nur für Claude – immer auf Deutsch, ohne `tr()`.
- Einstellungen: `ui_language`, `title_language`, `description_language` (je `en`/`de`); Standardwerte in `config.json`,
  Wahl des Nutzers in `data\settings.json` (Dialog „Einstellungen“ in der Zentrale oder `python -m vinted_hub settings [set key=value]`).
  Inserate: Titel/Beschreibung in der eingestellten Sprache, die Beschreibung immer nur in einer Sprache; jedes Inserat
  speichert `title_language` / `description_language`. Umschreiben in die andere Sprache nur auf Wunsch (Ablauf in CLAUDE.md).
- Keine persönlichen Daten ins Git (alles in `data\` und `0_input_photos\`, siehe `.gitignore`).
- Nie bei Vinted absenden/veröffentlichen, nie Passwörter eingeben, nichts endgültig löschen, nicht raten (Unsicheres → Frage),
  Preise setzt der Nutzer, `data\listings.json` nur gezielt über `vinted_hub.core.update_fields` / `tools\import_listings.py` ändern.
- Neue Fotos analysieren: `tools\contact_sheet.py` → Paare nach `data\items\NN_name\` kopieren → Einstellungen lesen
  (`python -m vinted_hub settings`) → Workflow `.claude\workflows\vinted-analysis.js` mit `{settings, items}` →
  `tools\import_listings.py` → Übersicht an den Nutzer; dabei die Sprachen im Workflow-Ergebnis (`settings` je Paar) mit
  `python -m vinted_hub settings` vergleichen und eine Abweichung erwähnen.
- Oberfläche der Zentrale: Preact + htm, eingebettet als eine Datei (`vinted_hub\web\vendor\preact-htm.js`) – **kein npm, kein
  Build-Schritt**, ES-Module in `vinted_hub\web\js\` (`state\`, `components\`, `views\listings|prices|stats\`, `i18n\`).
  Komponenten rufen Aktionen aus `js\state\` auf, Textfelder über `components\inputs.js`, nie `innerHTML`. Aufbau, Regeln,
  neue Texte/Ansichten, Bibliothek aktualisieren und Tests: `docs\FRONTEND.md` (Kurzfassung in CLAUDE.md, „Oberfläche der Zentrale (Code)“).
- Nach Änderungen an `vinted_hub\*.py` die Zentrale neu starten – auch nach einem Update, denn eine neuere Oberfläche
  (`vinted_hub\web\`) braucht den passenden Server.
