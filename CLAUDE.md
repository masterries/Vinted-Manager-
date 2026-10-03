# Vinted Zentrale – Arbeitsanweisung für Claude

Der Nutzer verkauft private Schuhe auf **vinted.lu** (Luxemburg). Dieses Projekt ist seine Verkaufs-Pipeline:
Fotos → Analyse durch Claude → lokale Web-„Zentrale“ (Prüfen, Fragen beantworten, Preise, Freigabe) →
Formular im Vinted-Chrome automatisch ausfüllen → **der Nutzer schickt selbst ab** → Statistik/Verkauf verfolgen.

- Mit dem Nutzer **Deutsch** sprechen, kurz und ohne Fachjargon.
- Code, Dateinamen, Befehle und JSON-Daten sind **Englisch**. Die Oberfläche ist **zweisprachig** (Deutsch/Englisch, Einstellung
  `ui_language`; der Nutzer nutzt Deutsch) – siehe „Einstellungen & Sprachen“ und „Namen (Code ↔ Oberfläche)“.
- Inseratstexte: Die Sprache von Titel und Beschreibung legen die Einstellungen fest (`title_language`, `description_language`,
  je `en` oder `de`). Die Beschreibung hat immer **genau eine Sprache** – kein zweiter Block, keine Übersetzung, keine Trennzeile.
  **Kurz und gegliedert** (Nutzerwunsch): ca. 150–400 Zeichen (Prüfwerkzeug: max. 700), Blöcke durch **eine Leerzeile** getrennt –
  1 Satz „was es ist“ · 2–4 Faktenzeilen (Größe, Material, Absatzhöhe ca. …) · 1 Satz Zustand passend zu `condition` · Hashtags
  in der Beschreibungssprache (ohne Umlaute) als letzte Zeile. Unsichere Angaben mit Marker in der
  Beschreibungssprache (`[? please confirm]` / `[? bitte bestätigen]`, `[?]` für unbekannte Werte); Fragen-Optionen ersetzen nur
  Text in der Sprache des Textes, den sie ändern. Das Prüfwerkzeug meldet Text in der falschen Sprache bei noch nicht eingestellten Inseraten.
- Windows 10, Python 3.9 (`.venv\Scripts\python.exe`). Kein `match`, keine `X | Y`-Typen zur Laufzeit.
- Code: Paket `vinted_hub\` (`core.py`, `i18n.py`, `chrome.py`, `form.py`, `commands.py`, `server.py`, `web\hub.html`),
  Werkzeuge in `tools\`, alle persönlichen Daten in `data\`.
- Kurzanleitung für den Nutzer: `docs\GUIDE.md` (Deutsch), `docs\GUIDE.en.md` (Englisch).

## Häufigster Auftrag: „Neue Fotos sind in 0_input_photos, bitte analysieren“

1. `.venv\Scripts\python.exe tools\contact_sheet.py` → listet neue (noch nicht einsortierte) Fotos mit Aufnahmezeit
   und schreibt `data\analysis\_contact_*.jpg`. Kontaktbögen ansehen (Read) und Fotos zu Paaren gruppieren
   (Aufnahmezeit + Aussehen; Karton-/Etikettfotos gehören zum Paar davor/danach).
2. Fotos nach `data\items\<NN_kurzname>\` **kopieren** (nicht verschieben). Nummerierung fortsetzen (höchste vorhandene Nummer
   in `data\items\` + 1). Originale bleiben in `0_input_photos`. HEIC ist ok (pillow-heif).
3. Dem Nutzer die Gruppierung als kleine Tabelle zeigen. Einstellungen lesen:
   `.venv\Scripts\python.exe -m vinted_hub settings` (eine JSON-Zeile, z. B.
   `{"ui_language": "de", "title_language": "en", "description_language": "en"}`), dann den gespeicherten Workflow starten:
   `Workflow({scriptPath: ".claude\\workflows\\vinted-analysis.js", args: {settings: <diese JSON-Zeile>, items: [{folder, photos: [...]}, ...]}})`
   (pro Paar ein Analyse- und ein Gegenprüf-Agent; schreibt `data\analysis\<folder>.json` mit Titel/Beschreibung in den
   eingestellten Sprachen und den Texten für den Verkäufer in `ui_language`, prüft selbst mit dem Prüfwerkzeug).
   Die alte Form `args: [{folder, photos}]` ohne Einstellungen gilt als Oberfläche `de`, Titel `en`, Beschreibung `en`.
   Unbekannte Schlüssel oder ungültige Werte in `settings` brechen mit einer Fehlermeldung ab. Das Ergebnis enthält je Paar
   `{folder, settings, analysis, review}` – `settings` sind die Sprachen, mit denen der Workflow wirklich gearbeitet hat.
4. Fertige Paare übernehmen – auch schon während andere noch laufen, wenn der Nutzer fragt (Fortschritt: `journal.jsonl` des Laufs,
   ein Paar ist fertig, wenn der Gegenprüf-Schritt `review:<folder>` ein Ergebnis hat):
   `.venv\Scripts\python.exe tools\import_listings.py <folder> ...`
   (prüft jedes Inserat, hängt nur neue an, überschreibt nichts Bearbeitetes).
5. Kurze Übersicht an den Nutzer: Marke, Größe, Zustand, Anzahl Fragen, Preisvorschlag, Auffälliges aus der Gegenprüfung.
   Die Sprachen im Workflow-Ergebnis (`settings` je Paar) mit `.venv\Scripts\python.exe -m vinted_hub settings` vergleichen;
   weichen sie ab (z. B. Einstellungen während des Laufs geändert oder Workflow ohne Einstellungen gestartet), das dem Nutzer
   sagen – die Inserate sind dann in der „falschen“ Sprache und können umgeschrieben werden (siehe unten).

## Die Zentrale (lokaler Server)

- Start für den Nutzer: `Start Hub.bat` → http://127.0.0.1:8765. Von Claude: im Hintergrund
  `.venv\Scripts\python.exe -u -m vinted_hub serve --no-browser` (PowerShell, `run_in_background`).
- Nach Änderungen an `vinted_hub\*.py` den Server **neu starten** (alten Prozess mit `vinted_hub serve` in der
  Kommandozeile beenden). `vinted_hub\web\hub.html` wird bei jedem Aufruf frisch von der Platte gelesen → nur Seite neu laden.
  Aber: eine `hub.html` aus einer neueren Version braucht den **passenden Server** – ein noch laufender alter Server liefert
  die neue Seite sofort aus, kennt aber ihre neuen API-Pfade nicht (z. B. Einstellungen: „Nicht gefunden“). Nach einem Update
  (neue Dateien kopiert) den Server deshalb sofort neu starten, bevor der Nutzer die Seite neu lädt.
- Ein zweiter Start auf demselben Port bricht absichtlich ab („läuft schon“).
- Ansichten: **Inserate** (Liste + Detail, roter Kasten „Fehlt noch“ mit Fragen-Knöpfen), **Preise** (Tabelle),
  **Statistik** (Kennzahl-Kacheln mit Sparkline, Verlaufs-Liniendiagramm und Balken je Inserat, Umschalter Aufrufe/Favoriten,
  Tabelle mit Sparklines; reines SVG in `vinted_hub\web\hub.html`, Farben `--viz-1` blau = Aufrufe, `--viz-2` orange = Favoriten,
  auf Farbsehschwäche geprüft – keine zweite y-Achse, Werte immer auch als Tabelle).
  Kopfzeile: Chrome-Status, „Alle freigegebenen ausfüllen“, „Statistik abrufen“, **Einstellungen** (Dialog für die drei Sprachen,
  siehe „Einstellungen & Sprachen“).
- Die Seite pollt `/api/status` (5 s) und lädt neu, wenn sich `data\listings.json` ändert; geänderte Einstellungen übernimmt
  sie beim nächsten Poll.

## Vinted-Chrome und Aufträge

- `python -m vinted_hub login` / `Vinted Login.bat` / Knopf „Öffnen“ startet einen **normalen** Chrome mit eigenem Profil
  (`data\browser-profile\`, Debug-Port 9222). Der Nutzer loggt sich **selbst** ein. Ein von Playwright gestarteter Browser wurde
  von Vinteds Bot-Erkennung blockiert – deshalb verbinden sich alle Befehle per CDP mit diesem Chrome.
- Befehle `python -m vinted_hub <befehl>` (laufen aus der Zentrale als Auftrag, nur einer gleichzeitig, oder per CLI):
  - `fill <folder>` – füllt Fotos, Titel, Beschreibung, Kategorie, Marke, Größe, Zustand, Farben, Material, Preis und die
    **Paketgröße** (Abschnitt „Shipping“: `package`, Standard Medium – Vinted schlägt für Schuhe oft Large vor) aus, liest Vinteds
    Preisempfehlung (`vinted_price`), wartet bis der Nutzer absendet und **erkennt dann selbst**, ob es online oder ein Entwurf ist:
    eine Abfrage der eigenen Artikelliste (wie `stats`, aus dem Vinted-Tab heraus) → Status `online`/`draft` + `vinted_id` + `vinted_url`.
    Klappt die Abfrage nicht: `draft` + Hinweis, „Statistik abrufen“ gleicht später ab. Paketgröße nicht gefunden → HTML-Ausschnitt in
    `data\debug\shipping_<folder>.html` (Selektoren in `form.py`, `select_package`).
  - `fill-approved [--only <folder>]` – dasselbe nacheinander für alle `approved`.
  - `prices [--only <folder>]` – nur Kategorie/Marke/Größe/Zustand wählen, Empfehlung lesen, Tab **ohne Speichern** schließen.
  - `stats` – öffnet das eigene Profil und liest per `/api/v2/wardrobe/<id>/items?per_page=96` Aufrufe (`view_count`),
    Favoriten, Status, Preis aller Artikel; speichert den Verlauf in `data\stats.json`, ordnet per `vinted_id`/Titel zu,
    setzt `vinted_stats` und gleicht Status ab (`sold`/`online`/`draft`).
  - `explore` – liest das Upload-Formular aus (wenn Vinted das Formular ändert, Selektoren in `vinted_hub\form.py` anpassen);
    `tools\explore_dropdowns.py` klickt die Auswahllisten durch (speichert nichts bei Vinted). Ausgaben landen in `data\debug\`.
  - `settings` – zeigt die Einstellungen als JSON; `settings set key=value ...` ändert sie (steuert keinen Chrome).
- Formular (englische Oberfläche): Auswahllisten `[data-testid=<name>-input]` öffnen, Optionen in `<name>-content` mit
  `role=radio|checkbox|button`; Vergleich über die **erste Textzeile** der Option. Kategorien z. B.
  `Women > Shoes > Boots > Ankle boots`, `Women > Shoes > Heels`, `… > Sandals`, `… > Espadrilles`, `… > Trainers`.

## Daten

- `data\listings.json` – Liste aller Inserate. Wichtige Felder: `folder`, `status` (`new`→`approved`→`draft`→`online`→`sold`,
  `on_hold`), `title`, `description`, `title_language` / `description_language` (`en`/`de`, Sprache von Titel/Beschreibung),
  `category`, `brand`, `size`, `condition` (Vinteds englische Bezeichnungen: New with tags /
  New without tags / Very good / Good / Satisfactory), `color` (englische Vinted-Farbnamen, max. 2), `material`, `heel_height`,
  `shape`, `package`, `price` (setzt **nur der Nutzer**), `suggested_price`, `price_reasoning`, `photos` (Reihenfolge,
  erstes = Titelbild), `hints`, `questions`, `history` (Rückgängig-Stapel), `analysis`, `vinted_price`, `vinted_id`,
  `vinted_url`, `vinted_stats`.
- `questions`: jede unsichere Angabe steht im Text mit Marker (`[? please confirm]` / `[? bitte bestätigen]` bzw. `[?]`) **und**
  als Frage mit Optionen `{label, input?, replace: [[old, new, optional?]], fields: {...}}`. Die Zentrale wendet die Ersetzungen auf
  Titel und Beschreibung an. Format-Details und Regeln stehen im Workflow `.claude\workflows\vinted-analysis.js`
  (Funktionen `languageRules` und `format`, Texttabellen `TEXT` / `UI` je Sprache).
- Prüfwerkzeug: `tools\check_listing.py <datei.json>` (jede Option findet ihre Textstelle, nach allen Antworten bleibt
  kein `[?`, keine kaputten Leerzeichen, einzelne Leerzeilen zwischen Blöcken erlaubt – keine doppelten, keine am Anfang/Ende –,
  Beschreibung max. 700 Zeichen solange nicht bei Vinted, Sprachregel siehe unten). Vor jeder Übernahme muss es OK melden.
- `data\settings.json` – die Einstellungen des Nutzers (siehe „Einstellungen & Sprachen“).
- `data\stats.json` – `{member_id, history: [{time, items: [{id, title, url, price, views, favorites, draft, sold, …}]}]}`.
- `data\items\<folder>\` Fotos (+ `_preview\`, `_upload\` werden automatisch erzeugt), `data\analysis\` Analyse-Ergebnisse
  und Crops, `data\archive\` alte/ausgemusterte Paare, `data\debug\` Debug-Ausgaben, `data\browser-profile\` Vinted-Login
  (nie anfassen).

## Einstellungen & Sprachen

| Schlüssel | Werte | Wirkung |
|---|---|---|
| `ui_language` | `en` / `de` | Sprache der Zentrale, der Auftrags-Protokolle, der Server-/CLI-Meldungen (nicht der Werkzeuge in `tools\`) und der Texte für den Verkäufer, die **neue** Analysen schreiben (Fragen, Erklärungen, Knöpfe, Platzhalter, Hinweise, Preisbegründung, Analyse-Notizen) |
| `title_language` | `en` / `de` | Sprache der Titel neuer Analysen (`en`: „… Size 39“, `de`: „… Gr. 39“) |
| `description_language` | `en` / `de` | Sprache der Beschreibungen neuer Analysen – immer genau eine Sprache, nie zweisprachig |

- Standardwerte stehen in `config.json` (im Git, alle `en`). Die Wahl des Nutzers steht in `data\settings.json` (persönlich,
  nicht im Git), z. B. `{"ui_language": "de", "title_language": "en", "description_language": "en"}`. `core.load_config()`
  liefert `config.json` plus die gültigen Werte aus `data\settings.json`; unbekannte Schlüssel und Werte werden ignoriert.
  `core.current_settings(config)` / `core.save_settings(config, changes)` lesen bzw. prüfen und speichern (atomar).
- Ändern: in der Zentrale über den Dialog **Einstellungen** (schreibt `data\settings.json`; zeigt auch Domain, Datenordner,
  Fotoordner und Ports), per CLI `.venv\Scripts\python.exe -m vinted_hub settings set description_language=de` (mehrere
  `key=value` möglich) oder per API `GET/POST /api/settings` (`{"changes": {...}}`). `/api/data` und `/api/status` liefern die
  aktuellen Einstellungen mit, damit andere offene Tabs sie übernehmen.
- Eine Änderung wirkt auf die Oberfläche sofort und auf **neue** Analysen; bestehende Inserate bleiben, wie sie sind.
  Jedes Inserat speichert seine eigenen Sprachen in `title_language` / `description_language` – neue Analysen schreiben sie,
  `tools\import_listings.py` ergänzt fehlende aus den aktuellen Einstellungen. (Die bisherigen Inserate sind alle Englisch und
  wurden einmalig auf `en`/`en` gesetzt.)
- Der Einstellungen-Dialog zeigt, wie viele noch nicht eingestellte Inserate (`new`/`on_hold`/`approved`) eine andere Titel- oder
  Beschreibungssprache haben als eingestellt, mit dem Hinweis, dass Claude sie umschreiben kann. Die Zentrale selbst übersetzt nicht.
- Sprachregel im Prüfwerkzeug (nur für `new`/`on_hold`/`approved`): maßgeblich sind `title_language` / `description_language`
  des Inserats (fehlen sie: die Einstellungen). Nie zweisprachig: jede Zeile, die nur aus einem Sprachnamen mit Verzierung besteht
  (`— Deutsch —`, `=== English ===`, `Deutsch:`, `–– EN ––` …), ist ein Fehler. Marker nur `[?]` oder in der Sprache des Textes
  (`en`: `[? please …]`, `de`: `[? bitte …]`). `en` → keine typisch deutschen Wörter/Zeilen (Größe, Zustand, Absatzhöhe, Glattleder,
  Karton, „Gr. 39“ / „Gr. [?]“ …); `de`-Beschreibung → keine englischen Zeilen/Wörter (`Size:`, `Heel height:`, `approx.`, leather,
  with, the …); `de`-Titel → nur strukturelle englische Wörter zählen („Size 39“ / „Size [?]“, Women's/Men's/Ladies, with, and).
  Englische Modell-/Farbnamen („Smooth Leather“, „Triple White“) bleiben im Titel erlaubt; in einer deutschen Beschreibung so einen
  Namen in „…“ setzen oder in `analysis.model` eintragen (Text in Anführungszeichen, Hashtags, Marke und `analysis.model` prüft das
  Werkzeug nicht). `Material:` ist in beiden Sprachen gleich. Die Regel gilt auch für den Text nach jeder einzelnen Antwort-Option
  (Ersetzungstexte). Ungültige Sprachwerte sind ein Fehler.

## Inserate in die andere Sprache umschreiben

Nur wenn der Nutzer es möchte (z. B. nach einer Änderung der Einstellungen). Die Zentrale kann das nicht, Claude macht es so:

1. Nur Inserate, die noch nicht bei Vinted sind: Status `new`, `on_hold`, `approved`. `draft`/`online`/`sold` nie umschreiben.
2. `title` und `description` sinngemäß neu in der Zielsprache schreiben – gleiche Fakten, nichts dazuerfinden, Zeilen und
   Hashtags wie im Workflow (`format`), genau eine Sprache. Marker mit umschreiben (`[? please confirm]` ↔ `[? bitte bestätigen]`, `[?]` bleibt).
3. Offene Fragen (ohne `answer`): die `replace`-Paare aller Optionen an den neuen Text anpassen (der alte Text muss wörtlich
   vorkommen). Die Fragen- und Knopftexte bleiben, wie sie sind (sie folgen nicht der Inseratssprache).
4. `history` (Rückgängig-Stapel): `title`/`description` in `before` und `after` jedes Eintrags ebenfalls umschreiben, damit
   „Rückgängig“ weiter funktioniert – das letzte `after` muss **genau** dem neuen aktuellen Text entsprechen, jedes `before`
   ist der Text vor dieser Antwort (mit Marker) in der neuen Sprache. Die `replace`-Paare der beantworteten Fragen mit Verlauf
   ebenfalls anpassen, denn „Rückgängig“ öffnet sie wieder.
5. `title_language` / `description_language` auf die neue Sprache setzen.
6. Prüfwerkzeug auf eine Kopie der geänderten Inserate laufen lassen (`tools\check_listing.py <datei.json>`), bis es OK meldet.
7. Schreiben mit einem kleinen Python-Skript: `with core.file_lock(config):` frisch `core.read_listings(config)`, nur die
   umgeschriebenen Felder (`title`, `description`, `questions`, `history`, Sprachfelder) der betroffenen Inserate setzen –
   vorher prüfen, dass `updated_at` noch dem gelesenen Stand entspricht, sonst dieses Inserat auslassen und neu machen –,
   dann `core.write_listings(config, listings)`. **Nie** `data\listings.json` aus einem alten Stand komplett überschreiben.

## Namen (Code ↔ Oberfläche)

Code-Bezeichner, Datei-/Ordnernamen, Befehle, API-Pfade, JSON-Schlüssel und gespeicherte Werte sind **Englisch**.
Die Oberfläche ist **zweisprachig** (`ui_language`): Alle sichtbaren Texte (Zentrale, Fehlermeldungen, Auftrags-Protokolle,
CLI-Ausgaben) stehen im Code auf **Englisch**; die deutsche Übersetzung steht je Seite in genau einem Wörterbuch –
Python: `DE` in `vinted_hub\i18n.py` (`tr("Photo missing: {files}", files=...)`), Oberfläche: `const DE` in
`vinted_hub\web\hub.html` (`t("English text {name}", {name})`). **Jeder neue sichtbare Text braucht beide Fassungen**
(englischer Quelltext + deutscher Eintrag mit denselben `{Platzhaltern}`). Deutsche Formulierungen, die der Nutzer kennt,
bleiben; Englisch kurz, schlicht und in **britischer** Schreibweise (favourites, colour, analyse, recognised).
Produktname: de „Vinted Zentrale“, en „Vinted Hub“.
**Ausnahme:** Die Werkzeuge in `tools\` (Prüfwerkzeug `check_listing.py`, `import_listings.py`, `contact_sheet.py`,
`explore_dropdowns.py`) melden nur für Claude und daher immer auf **Deutsch**, unabhängig von `ui_language`; sie laufen nicht
über `tr()` und brauchen keinen Eintrag in `DE`. Der Workflow lässt die letzte Zeile des Prüfwerkzeugs („OK: …“) deshalb
unverändert zitieren.

Gespeicherte Werte bleiben Englisch, die Zentrale übersetzt nur ihre **Anzeige** (Tabelle unten); Auswahllisten speichern
den englischen Wert. Texte in den Inseraten (`title`, `description`, `question`, `explanation`, `label`, `placeholder`, `button`,
`note`, `notes`, `hints`, `price_reasoning`, `analysis`) werden so angezeigt, wie sie gespeichert sind – nie maschinell übersetzt.
Neue Analysen schreiben die Texte für den Verkäufer in `ui_language`, Titel/Beschreibung in `title_language` / `description_language`.

| Feld | Wert im Code/JSON → Anzeige de / en |
|---|---|
| `status` | `new` → Zu prüfen / To review · `on_hold` → Zurückgestellt / On hold · `approved` → Freigegeben / Approved · `draft` → Entwurf bei Vinted / Draft on Vinted · `online` → Online / Online · `sold` → Verkauft / Sold |
| `condition` | `New with tags` → Neu mit Etikett · `New without tags` → Neu ohne Etikett · `Very good` → Sehr gut · `Good` → Gut · `Satisfactory` → Zufriedenstellend (en: wie gespeichert) |
| `package` | `Small` → Klein / Small · `Medium` → Mittel / Medium · `Large` → Groß / Large (wird beim Ausfüllen gewählt; Nutzerwunsch: **Medium**, Large nur für wirklich große Schuhe wie Overknees/Schneestiefel, nie Small) |
| `color` | Vinteds englische Namen, kommagetrennt, max. 2 (z. B. `Black`, `White`, `Beige`, `Brown`, `Navy`, `Multi`) |
| `material` | `Leather`, `Suede`, `Faux leather`, `Canvas`, `Rubber`, `Jute` oder leer; unsicher mit Präfix `probably ` (wird nicht ausgefüllt) |
| `brand` / `size` | `No brand` → Ohne Marke / No brand (beim Ausfüllen wird in Vinteds Markenliste „List without brand“ gewählt, `#empty-brand`); unbekannt = `unknown` (bleibt leer) |
| `title_language` / `description_language` | `en` / `de` |

Wichtige Schlüssel (Bedeutung → JSON):

| Bereich | Schlüssel |
|---|---|
| Inserat | Ordner `folder`, Titel `title`, Beschreibung `description`, Titelsprache `title_language`, Beschreibungssprache `description_language`, Kategorie `category`, Marke `brand`, Größe `size`, Zustand `condition`, Farbe `color`, Absatzhöhe `heel_height`, Schuhform `shape`, Paket `package`, Preis `price`, Mindestpreis `min_price`, Preisvorschlag `suggested_price` / `suggested_min_price`, Preisbegründung `price_reasoning`, Fotos `photos`, Hinweise `hints`, Fragen `questions`, Verlauf `history`, Notiz `notes`, Analyse `analysis`, geändert `updated_at` |
| Frage | `{id, field?, question, explanation?, options: [{label, input?, placeholder?, button?, replace, fields}], answer?, note?}`, Platzhalter `{value}` |
| Rückgängig | `history: [{question, before, after}]` |
| Vinted-Preis | `vinted_price: {bargain, optimal, premium, date}` (günstig / optimal / premium / Datum) |
| Statistik | `vinted_stats` und `data\stats.json`: Aufrufe `views`, Favoriten `favorites`, Zeit `time`, Mitglied `member_id` |
| Einstellungen | `data\settings.json` / `config.json`: Oberflächensprache `ui_language`, Titelsprache `title_language`, Beschreibungssprache `description_language` |
| Ansichten / Aufträge | Ansichten `listings` (Inserate), `prices` (Preise), `stats` (Statistik); Aufträge (Code: Jobs) `fill`, `fill_approved`, `prices`, `stats` |

## Git

- Ins Repo gehören nur Code, Doku und `docs\images\`. **Keine persönlichen Daten**: `0_input_photos\` und alles in `data\`
  (Fotos, `listings.json`, `stats.json`, `settings.json`, `analysis\`, `archive\`, `debug\` (enthält Vinted-Seiten mit Kontodaten),
  `browser-profile\`) – alles in `.gitignore`.
  Vor jedem Commit `git status` prüfen; neue Ordner mit Nutzerdaten sofort in `.gitignore` aufnehmen.
- README-Screenshots (`docs\images\`) stammen aus einer Test-Kopie der Zentrale (eigener Port, Beispiel-Statistik) bzw. einem
  zugeschnittenen Formular-Screenshot ohne Profilbild/Nachrichten. Beim Erneuern genauso vorgehen.
- Commits/Push nur, wenn der Nutzer es möchte.

## Regeln (vom Nutzer so gewollt)

- **Niemals bei Vinted absenden, veröffentlichen, löschen oder Nachrichten schicken.** Skripte füllen nur aus; der Nutzer klickt.
- **Nie Passwörter eingeben**, keine Captchas lösen. Der Nutzer loggt sich selbst ein.
- **Nicht raten:** Marke nur aus lesbarem Text/Logo, Größe nur aus einer gelesenen Zahl. Unsicheres → Marker + Frage.
  Der Nutzer will die Beschreibung **nie von Hand** bearbeiten – Hinweise (`hints`) dürfen nie „Text ändern/[?] löschen“ verlangen.
- **Beschreibung nicht kritisch, nicht ultra detailliert:** Mängel nur nennen, wenn wirklich etwas kaputt ist (Loch, Riss, Absatz
  locker/abgebrochen, Sohle löst sich, Material durchgescheuert, Teil fehlt, Fleck geht nicht raus) – kurz, „(see photos)“. Normale
  Gebrauchsspuren (leichte Kratzer, Knicke, Staub, Innensohlen-Spuren, Mini-Flecken) nicht erwähnen; sie gehören nur in
  `analysis.flaws` und in eine ehrliche `condition`-Stufe. Keine `Shape:`-Zeile, keine internen Details (Herstellerzeichen, Codes, Preisaufkleber).
- **Preise legt der Nutzer fest.** Analyse schreibt nur `suggested_price`; Vinteds Empfehlung ist nur Info.
- **`data\listings.json` nie aus einem alten Stand komplett überschreiben** – der Nutzer arbeitet parallel in der Zentrale.
  Nur über `vinted_hub.core.update_fields` / `update_many` (mit Dateisperre `data\listings.lock`) oder
  `tools\import_listings.py` schreiben. Bei eigenen Datenkorrekturen: kleines Python-Skript, das frisch liest
  (`read_listings`), gezielt Felder ändert und `vinted_hub.core.write_listings` nutzt.
- **Nichts endgültig löschen.** „Löschen“ heißt: nach `data\archive\<datum>_<name>\` verschieben; der Nutzer löscht selbst.
- Vinted-AGB verbieten Automatisierung; der Nutzer hat das Risiko bewusst akzeptiert (kleiner Privatgebrauch) – nicht erneut
  diskutieren, aber schonend arbeiten: ein Inserat nach dem anderen, Mensch klickt ab, 3–6 neue Inserate pro Tag empfehlen,
  Statistik höchstens ~1× täglich.
- Tests an Kopien (eigener Port über `hub_port`, z. B. 8790, `chrome_port` auf einen freien Wert), nie destruktiv gegen
  Port 8765 oder die echte `data\listings.json`; niemals Aufträge starten, die den echten Vinted-Chrome steuern, ohne dass
  der Nutzer es will.

## Stolpersteine

- Bash-Heredocs mit Apostrophen (`Levi's`, `Women's`) brechen ab → Python-Skript als Datei schreiben und ausführen.
- PowerShell 5.1 `Set-Content -Encoding UTF8` schreibt ein BOM – Lesecode nutzt `utf-8-sig`.
- `os.replace` scheitert unter Windows, wenn die Zieldatei offen ist → `write_listings` wiederholt automatisch.
- Fotos öffnen immer über `vinted_hub.core.open_image(path)` (HEIC + EXIF-Drehung); Upload-Fotos ohne Metadaten (GPS) über
  `vinted_hub.core.prepare_upload_photos`.
- Preisfeld der englischen Oberfläche erwartet Punkt als Dezimaltrenner.
