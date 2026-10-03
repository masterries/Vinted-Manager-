# Vinted Zentrale – Arbeitsanweisung für Claude

Der Nutzer verkauft private Schuhe auf **vinted.lu** (Luxemburg). Dieses Projekt ist seine Verkaufs-Pipeline:
Fotos → Analyse durch Claude → lokale Web-„Zentrale“ (Prüfen, Fragen beantworten, Preise, Freigabe) →
Formular im Vinted-Chrome automatisch ausfüllen → **der Nutzer schickt selbst ab** → Statistik/Verkauf verfolgen.

- Mit dem Nutzer **Deutsch** sprechen, kurz und ohne Fachjargon.
- Code, Dateinamen, Befehle und JSON-Daten sind **Englisch**, die Oberfläche und alle Texte für den Nutzer **Deutsch** –
  Zuordnung siehe Abschnitt „Namen (Code ↔ Oberfläche)“.
- Inseratstexte: **Titel Englisch**, **Beschreibung immer zweisprachig** (`config.json` → `"listing_language": "en+de"`):
  englischer Block, dann eine Zeile genau `— Deutsch —`, dann derselbe Inhalt auf Deutsch, Hashtags einmal am Ende,
  max. 2000 Zeichen. Unsichere Angaben stehen in beiden Blöcken mit Marker (`[? please confirm]` / `[? bitte bestätigen]`),
  und jede Fragen-Option braucht Ersetzungen für **beide** Sprachen. Das Prüfwerkzeug erzwingt das für noch nicht
  eingestellte Inserate.
- Windows 10, Python 3.9 (`.venv\Scripts\python.exe`). Kein `match`, keine `X | Y`-Typen zur Laufzeit.
- Code: Paket `vinted_hub\` (`core.py`, `chrome.py`, `form.py`, `commands.py`, `server.py`, `web\hub.html`),
  Werkzeuge in `tools\`, alle persönlichen Daten in `data\`.
- Kurzanleitung für den Nutzer: `docs\GUIDE.md`.

## Häufigster Auftrag: „Neue Fotos sind in 0_input_photos, bitte analysieren“

1. `.venv\Scripts\python.exe tools\contact_sheet.py` → listet neue (noch nicht einsortierte) Fotos mit Aufnahmezeit
   und schreibt `data\analysis\_contact_*.jpg`. Kontaktbögen ansehen (Read) und Fotos zu Paaren gruppieren
   (Aufnahmezeit + Aussehen; Karton-/Etikettfotos gehören zum Paar davor/danach).
2. Fotos nach `data\items\<NN_kurzname>\` **kopieren** (nicht verschieben). Nummerierung fortsetzen (höchste vorhandene Nummer
   in `data\items\` + 1). Originale bleiben in `0_input_photos`. HEIC ist ok (pillow-heif).
3. Dem Nutzer die Gruppierung als kleine Tabelle zeigen, dann den gespeicherten Workflow starten:
   `Workflow({scriptPath: ".claude\\workflows\\vinted-analysis.js", args: [{folder, photos: [...]}, ...]})`
   (pro Paar ein Analyse- und ein Gegenprüf-Agent; schreibt `data\analysis\<folder>.json`, prüft selbst mit dem Prüfwerkzeug).
4. Fertige Paare übernehmen – auch schon während andere noch laufen, wenn der Nutzer fragt (Fortschritt: `journal.jsonl` des Laufs,
   ein Paar ist fertig, wenn der Gegenprüf-Schritt `review:<folder>` ein Ergebnis hat):
   `.venv\Scripts\python.exe tools\import_listings.py <folder> ...`
   (prüft jedes Inserat, hängt nur neue an, überschreibt nichts Bearbeitetes).
5. Kurze Übersicht an den Nutzer: Marke, Größe, Zustand, Anzahl Fragen, Preisvorschlag, Auffälliges aus der Gegenprüfung.

## Die Zentrale (lokaler Server)

- Start für den Nutzer: `Start Hub.bat` → http://127.0.0.1:8765. Von Claude: im Hintergrund
  `.venv\Scripts\python.exe -u -m vinted_hub serve --no-browser` (PowerShell, `run_in_background`).
- Nach Änderungen an `vinted_hub\*.py` den Server **neu starten** (alten Prozess mit `vinted_hub serve` in der
  Kommandozeile beenden). `vinted_hub\web\hub.html` wird bei jedem Aufruf frisch von der Platte gelesen → nur Seite neu laden.
- Ein zweiter Start auf demselben Port bricht absichtlich ab („läuft schon“).
- Ansichten: **Inserate** (Liste + Detail, roter Kasten „Fehlt noch“ mit Fragen-Knöpfen), **Preise** (Tabelle),
  **Statistik** (Kennzahl-Kacheln mit Sparkline, Verlaufs-Liniendiagramm und Balken je Inserat, Umschalter Aufrufe/Favoriten,
  Tabelle mit Sparklines; reines SVG in `vinted_hub\web\hub.html`, Farben `--viz-1` blau = Aufrufe, `--viz-2` orange = Favoriten,
  auf Farbsehschwäche geprüft – keine zweite y-Achse, Werte immer auch als Tabelle).
  Kopfzeile: Chrome-Status, „Alle freigegebenen ausfüllen“, „Statistik abrufen“.
- Die Seite pollt `/api/status` (5 s) und lädt neu, wenn sich `data\listings.json` ändert.

## Vinted-Chrome und Aufträge

- `python -m vinted_hub login` / `Vinted Login.bat` / Knopf „Öffnen“ startet einen **normalen** Chrome mit eigenem Profil
  (`data\browser-profile\`, Debug-Port 9222). Der Nutzer loggt sich **selbst** ein. Ein von Playwright gestarteter Browser wurde
  von Vinteds Bot-Erkennung blockiert – deshalb verbinden sich alle Befehle per CDP mit diesem Chrome.
- Befehle `python -m vinted_hub <befehl>` (laufen aus der Zentrale als Auftrag, nur einer gleichzeitig, oder per CLI):
  - `fill <folder>` – füllt Fotos, Titel, Beschreibung, Kategorie, Marke, Größe, Zustand, Farben, Material, Preis aus,
    liest Vinteds Preisempfehlung (`vinted_price`), wartet bis der Nutzer absendet → Status `draft` + `vinted_url`.
  - `fill-approved [--only <folder>]` – dasselbe nacheinander für alle `approved`.
  - `prices [--only <folder>]` – nur Kategorie/Marke/Größe/Zustand wählen, Empfehlung lesen, Tab **ohne Speichern** schließen.
  - `stats` – öffnet das eigene Profil und liest per `/api/v2/wardrobe/<id>/items?per_page=96` Aufrufe (`view_count`),
    Favoriten, Status, Preis aller Artikel; speichert den Verlauf in `data\stats.json`, ordnet per `vinted_id`/Titel zu,
    setzt `vinted_stats` und gleicht Status ab (`sold`/`online`/`draft`).
  - `explore` – liest das Upload-Formular aus (wenn Vinted das Formular ändert, Selektoren in `vinted_hub\form.py` anpassen);
    `tools\explore_dropdowns.py` klickt die Auswahllisten durch (speichert nichts bei Vinted). Ausgaben landen in `data\debug\`.
- Formular (englische Oberfläche): Auswahllisten `[data-testid=<name>-input]` öffnen, Optionen in `<name>-content` mit
  `role=radio|checkbox|button`; Vergleich über die **erste Textzeile** der Option. Kategorien z. B.
  `Women > Shoes > Boots > Ankle boots`, `Women > Shoes > Heels`, `… > Sandals`, `… > Espadrilles`, `… > Trainers`.

## Daten

- `data\listings.json` – Liste aller Inserate. Wichtige Felder: `folder`, `status` (`new`→`approved`→`draft`→`online`→`sold`,
  `on_hold`), `title`, `description`, `category`, `brand`, `size`, `condition` (Vinteds englische Bezeichnungen: New with tags /
  New without tags / Very good / Good / Satisfactory), `color` (englische Vinted-Farbnamen, max. 2), `material`, `heel_height`,
  `shape`, `package`, `price` (setzt **nur der Nutzer**), `suggested_price`, `price_reasoning`, `photos` (Reihenfolge,
  erstes = Titelbild), `hints`, `questions`, `history` (Rückgängig-Stapel), `analysis`, `vinted_price`, `vinted_id`,
  `vinted_url`, `vinted_stats`.
- `questions`: jede unsichere Angabe steht im Text mit Marker (`[? please confirm]` bzw. `[?]`) **und** als Frage mit Optionen
  `{label, input?, replace: [[old, new, optional?]], fields: {...}}`. Die Zentrale wendet die Ersetzungen auf Titel und
  Beschreibung an. Format-Details und Regeln stehen im Workflow `.claude\workflows\vinted-analysis.js` (Konstante `FORMAT`).
- Prüfwerkzeug: `tools\check_listing.py <datei.json>` (jede Option findet ihre Textstelle, nach allen Antworten bleibt
  kein `[?`, keine kaputten Leerzeichen). Vor jeder Übernahme muss es OK melden.
- `data\stats.json` – `{member_id, history: [{time, items: [{id, title, url, price, views, favorites, draft, sold, …}]}]}`.
- `data\items\<folder>\` Fotos (+ `_preview\`, `_upload\` werden automatisch erzeugt), `data\analysis\` Analyse-Ergebnisse
  und Crops, `data\archive\` alte/ausgemusterte Paare, `data\debug\` Debug-Ausgaben, `data\browser-profile\` Vinted-Login
  (nie anfassen).

## Namen (Code ↔ Oberfläche)

Code-Bezeichner, Datei-/Ordnernamen, Befehle, API-Pfade, JSON-Schlüssel und gespeicherte Werte sind **Englisch**.
Alles, was der Nutzer sieht oder liest, bleibt **Deutsch**: Oberfläche der Zentrale, Fehlermeldungen, CLI-Ausgaben und in den
Daten die Texte `question`, `explanation`, `label`, `placeholder`, `button`, `note`, `hints`, `price_reasoning` sowie der
deutsche Teil der Beschreibung. Die Zentrale zeigt Werte über Tabellen in `vinted_hub\web\hub.html` deutsch an
(`STATUS_LABEL`, `CONDITION_LABEL`, `PACKAGE_LABEL`); Auswahllisten speichern den englischen Wert.

| Feld | Wert im Code/JSON → Anzeige |
|---|---|
| `status` | `new` → Zu prüfen · `on_hold` → Zurückgestellt · `approved` → Freigegeben · `draft` → Entwurf bei Vinted · `online` → Online · `sold` → Verkauft |
| `condition` | `New with tags` → Neu mit Etikett · `New without tags` → Neu ohne Etikett · `Very good` → Sehr gut · `Good` → Gut · `Satisfactory` → Zufriedenstellend |
| `package` | `Small` → Klein · `Medium` → Mittel · `Large` → Groß (Vinted schlägt die Paketgröße selbst vor, wird nicht ausgefüllt) |
| `color` | Vinteds englische Namen, kommagetrennt, max. 2 (z. B. `Black`, `White`, `Beige`, `Brown`, `Navy`, `Multi`) |
| `material` | `Leather`, `Suede`, `Faux leather`, `Canvas`, `Rubber`, `Jute` oder leer; unsicher mit Präfix `probably ` (wird nicht ausgefüllt) |
| `brand` / `size` | `No brand` = „Ohne Marke“ (wird nicht ausgefüllt); unbekannt = `unknown` |

Wichtige Schlüssel (Bedeutung → JSON):

| Bereich | Schlüssel |
|---|---|
| Inserat | Ordner `folder`, Titel `title`, Beschreibung `description`, Kategorie `category`, Marke `brand`, Größe `size`, Zustand `condition`, Farbe `color`, Absatzhöhe `heel_height`, Schuhform `shape`, Paket `package`, Preis `price`, Mindestpreis `min_price`, Preisvorschlag `suggested_price` / `suggested_min_price`, Preisbegründung `price_reasoning`, Fotos `photos`, Hinweise `hints`, Fragen `questions`, Verlauf `history`, Notiz `notes`, Analyse `analysis`, geändert `updated_at` |
| Frage | `{id, field?, question, explanation?, options: [{label, input?, placeholder?, button?, replace, fields}], answer?, note?}`, Platzhalter `{value}` |
| Rückgängig | `history: [{question, before, after}]` |
| Vinted-Preis | `vinted_price: {bargain, optimal, premium, date}` (günstig / optimal / premium / Datum) |
| Statistik | `vinted_stats` und `data\stats.json`: Aufrufe `views`, Favoriten `favorites`, Zeit `time`, Mitglied `member_id` |
| Ansichten / Aufträge | Ansichten `listings` (Inserate), `prices` (Preise), `stats` (Statistik); Aufträge (Code: Jobs) `fill`, `fill_approved`, `prices`, `stats` |

## Git

- Ins Repo gehören nur Code, Doku und `docs\images\`. **Keine persönlichen Daten**: `0_input_photos\` und alles in `data\`
  (Fotos, `listings.json`, `stats.json`, `analysis\`, `archive\`, `debug\` (enthält Vinted-Seiten mit Kontodaten),
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
