# AGENTS.md

Die vollständige Arbeitsanweisung für KI-Agenten steht in **[CLAUDE.md](CLAUDE.md)** – bitte zuerst dort lesen.

Kurzfassung:
- Projekt: Verkaufs-Pipeline für private Schuhe auf vinted.lu (Fotos → Analyse → lokale „Zentrale“ → Vinted-Formular ausfüllen).
  Code im Paket `vinted_hub\` (`python -m vinted_hub serve|login|fill|fill-approved|prices|stats|explore`), Werkzeuge in `tools\`.
- Mit dem Nutzer Deutsch sprechen; Inserate: Titel Englisch, Beschreibung immer Englisch + Deutsch.
  Code, Dateinamen und JSON-Daten sind Englisch, die Oberfläche Deutsch (Zuordnung in CLAUDE.md, „Namen (Code ↔ Oberfläche)“).
- Keine persönlichen Daten ins Git (alles in `data\` und `0_input_photos\`, siehe `.gitignore`).
- Nie bei Vinted absenden/veröffentlichen, nie Passwörter eingeben, nichts endgültig löschen, nicht raten (Unsicheres → Frage),
  Preise setzt der Nutzer, `data\listings.json` nur gezielt über `vinted_hub.core.update_fields` / `tools\import_listings.py` ändern.
- Neue Fotos analysieren: `tools\contact_sheet.py` → Paare nach `data\items\NN_name\` kopieren → Workflow
  `.claude\workflows\vinted-analysis.js` → `tools\import_listings.py`.
