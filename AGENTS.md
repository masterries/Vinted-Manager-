# AGENTS.md

Die vollständige Arbeitsanweisung für KI-Agenten steht in **[CLAUDE.md](CLAUDE.md)** – bitte zuerst dort lesen.

Kurzfassung:
- Projekt: Verkaufs-Pipeline für private Schuhe auf vinted.lu (Fotos → Analyse → lokale „Zentrale“ → Vinted-Formular ausfüllen).
- Mit dem Nutzer Deutsch sprechen; Inserate: Titel Englisch, Beschreibung immer Englisch + Deutsch.
- Keine persönlichen Daten ins Git (siehe `.gitignore`).
- Nie bei Vinted absenden/veröffentlichen, nie Passwörter eingeben, nichts endgültig löschen, nicht raten (Unsicheres → Frage),
  Preise setzt der Nutzer, `inserate.json` nur gezielt über `vinted.setze_felder` / `werkzeuge\uebernehmen.py` ändern.
- Neue Fotos analysieren: `werkzeuge\kontaktbogen.py` → Paare nach `schuhe\NN_name\` kopieren → Workflow
  `.claude\workflows\vinted-analyse.js` → `werkzeuge\uebernehmen.py`.
