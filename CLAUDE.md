# Vinted Zentrale – Arbeitsanweisung für Claude

Der Nutzer verkauft private Schuhe auf **vinted.lu** (Luxemburg). Dieses Projekt ist seine Verkaufs-Pipeline:
Fotos → Analyse durch Claude → lokale Web-„Zentrale“ (Prüfen, Fragen beantworten, Preise, Freigabe) →
Formular im Vinted-Chrome automatisch ausfüllen → **der Nutzer schickt selbst ab** → Statistik/Verkauf verfolgen.

- Mit dem Nutzer **Deutsch** sprechen, kurz und ohne Fachjargon.
- Inseratstexte: **Titel Englisch**, **Beschreibung immer zweisprachig** (`config.json` → `"sprache_inseratstext": "en+de"`):
  englischer Block, dann eine Zeile genau `— Deutsch —`, dann derselbe Inhalt auf Deutsch, Hashtags einmal am Ende,
  max. 2000 Zeichen. Unsichere Angaben stehen in beiden Blöcken mit Marker (`[? please confirm]` / `[? bitte bestätigen]`),
  und jede Fragen-Option braucht Ersetzungen für **beide** Sprachen. Das Prüfwerkzeug erzwingt das für noch nicht
  eingestellte Inserate.
- Windows 10, Python 3.9 (`.venv\Scripts\python.exe`). Kein `match`, keine `X | Y`-Typen zur Laufzeit.
- Kurzanleitung für den Nutzer: `ANLEITUNG.md`.

## Häufigster Auftrag: „Neue Fotos sind in 0_input_foto, bitte analysieren“

1. `.venv\Scripts\python.exe werkzeuge\kontaktbogen.py` → listet neue (noch nicht einsortierte) Fotos mit Aufnahmezeit
   und schreibt `analyse\_kontakt_*.jpg`. Kontaktbögen ansehen (Read) und Fotos zu Paaren gruppieren
   (Aufnahmezeit + Aussehen; Karton-/Etikettfotos gehören zum Paar davor/danach).
2. Fotos nach `schuhe\<NN_kurzname>\` **kopieren** (nicht verschieben). Nummerierung fortsetzen (höchste vorhandene Nummer
   in `schuhe\` + 1). Originale bleiben in `0_input_foto`. HEIC ist ok (pillow-heif).
3. Dem Nutzer die Gruppierung als kleine Tabelle zeigen, dann den gespeicherten Workflow starten:
   `Workflow({scriptPath: ".claude\\workflows\\vinted-analyse.js", args: [{ordner, fotos: [...]}, ...]})`
   (pro Paar ein Analyse- und ein Gegenprüf-Agent; schreibt `analyse\<ordner>.json`, prüft selbst mit dem Prüfwerkzeug).
4. Fertige Paare übernehmen – auch schon während andere noch laufen, wenn der Nutzer fragt (Fortschritt: `journal.jsonl` des Laufs,
   ein Paar ist fertig, wenn `pruefen:<ordner>` ein Ergebnis hat):
   `.venv\Scripts\python.exe werkzeuge\uebernehmen.py <ordner> ...`
   (prüft jedes Inserat, hängt nur neue an, überschreibt nichts Bearbeitetes).
5. Kurze Übersicht an den Nutzer: Marke, Größe, Zustand, Anzahl Fragen, Preisvorschlag, Auffälliges aus der Gegenprüfung.

## Die Zentrale (lokaler Server)

- Start für den Nutzer: `Freigabe starten.bat` → http://127.0.0.1:8765. Von Claude: im Hintergrund
  `.venv\Scripts\python.exe -u vinted.py freigabe --kein-browser` (PowerShell, `run_in_background`).
- Nach Änderungen an `freigabe.py`/`vinted.py` den Server **neu starten** (alten Prozess mit `vinted.py freigabe` in der
  Kommandozeile beenden). `web\freigabe.html` wird bei jedem Aufruf frisch von der Platte gelesen → nur Seite neu laden.
- Ein zweiter Start auf demselben Port bricht absichtlich ab („läuft schon“).
- Ansichten: **Inserate** (Liste + Detail, roter Kasten „Fehlt noch“ mit Fragen-Knöpfen), **Preise** (Tabelle),
  **Statistik** (Kennzahl-Kacheln mit Sparkline, Verlaufs-Liniendiagramm und Balken je Inserat, Umschalter Aufrufe/Favoriten,
  Tabelle mit Sparklines; reines SVG in `web/freigabe.html`, Farben `--viz-1` blau = Aufrufe, `--viz-2` orange = Favoriten,
  auf Farbsehschwäche geprüft – keine zweite y-Achse, Werte immer auch als Tabelle).
  Kopfzeile: Chrome-Status, „Alle freigegebenen ausfüllen“, „Statistik abrufen“.
- Die Seite pollt `/api/status` (5 s) und lädt neu, wenn sich `inserate.json` ändert.

## Vinted-Chrome und Aufträge

- `vinted.py login` / `Vinted Login.bat` / Knopf „Öffnen“ startet einen **normalen** Chrome mit eigenem Profil
  (`browser-profil\`, Debug-Port 9222). Der Nutzer loggt sich **selbst** ein. Ein von Playwright gestarteter Browser wurde
  von Vinteds Bot-Erkennung blockiert – deshalb verbinden sich alle Befehle per CDP mit diesem Chrome.
- Befehle (laufen aus der Zentrale als Auftrag, nur einer gleichzeitig, oder per CLI):
  - `ausfuellen <ordner>` – füllt Fotos, Titel, Beschreibung, Kategorie, Marke, Größe, Zustand, Farben, Material, Preis aus,
    liest Vinteds Preisempfehlung (`vinted_preis`), wartet bis der Nutzer absendet → Status `entwurf` + `vinted_url`.
  - `hochladen` – dasselbe nacheinander für alle `freigegeben`.
  - `preise` – nur Kategorie/Marke/Größe/Zustand wählen, Empfehlung lesen, Tab **ohne Speichern** schließen.
  - `statistik` – öffnet das eigene Profil und liest per `/api/v2/wardrobe/<id>/items?per_page=96` Aufrufe (`view_count`),
    Favoriten, Status, Preis aller Artikel; speichert den Verlauf in `statistik.json`, ordnet per `vinted_id`/Titel zu,
    setzt `vinted_stats` und gleicht Status ab (verkauft/online/entwurf).
  - `erkunden` – liest das Upload-Formular aus (wenn Vinted das Formular ändert, Selektoren in `vinted.py` anpassen);
    `werkzeuge\dropdowns_erkunden.py` klickt die Auswahllisten durch (speichert nichts bei Vinted). Ausgaben landen in `erkunden\`.
- Formular (englische Oberfläche): Auswahllisten `[data-testid=<name>-input]` öffnen, Optionen in `<name>-content` mit
  `role=radio|checkbox|button`; Vergleich über die **erste Textzeile** der Option. Kategorien z. B.
  `Women > Shoes > Boots > Ankle boots`, `Women > Shoes > Heels`, `… > Sandals`, `… > Espadrilles`, `… > Trainers`.

## Daten

- `inserate.json` – Liste aller Inserate. Wichtige Felder: `ordner`, `status` (`neu`→`freigegeben`→`entwurf`→`online`→`verkauft`,
  `zurueckgestellt`), `titel`, `beschreibung`, `kategorie`, `marke`, `groesse`, `zustand` (Neu mit Etikett / Neu ohne Etikett /
  Sehr gut / Gut / Zufriedenstellend), `farbe` (deutsche Farbnamen, max. 2), `material`, `absatzhoehe`, `schuhform`, `paket`,
  `preis` (setzt **nur der Nutzer**), `preis_vorschlag`, `preis_begruendung`, `fotos` (Reihenfolge, erstes = Titelbild),
  `hinweise`, `fragen`, `verlauf` (Rückgängig-Stapel), `analyse`, `vinted_preis`, `vinted_id`, `vinted_url`, `vinted_stats`.
- `fragen`: jede unsichere Angabe steht im Text mit Marker (`[? please confirm]` bzw. `[?]`) **und** als Frage mit Optionen
  `{label, eingabe?, ersetzen: [[alt, neu, optional?]], felder: {...}}`. Die Zentrale wendet die Ersetzungen auf Titel und
  Beschreibung an. Format-Details und Regeln stehen im Workflow `.claude\workflows\vinted-analyse.js` (Konstante `FORMAT`).
- Prüfwerkzeug: `werkzeuge\pruefe_inserat.py <datei.json>` (jede Option findet ihre Textstelle, nach allen Antworten bleibt
  kein `[?`, keine kaputten Leerzeichen). Vor jeder Übernahme muss es OK melden.
- `statistik.json` – `{mitglied_id, verlauf: [{zeit, artikel: [{id, titel, url, preis, aufrufe, favoriten, entwurf, verkauft, …}]}]}`.
- `schuhe\<ordner>\` Fotos (+ `_vorschau\`, `_upload\` werden automatisch erzeugt), `analyse\` Analyse-Ergebnisse und Crops,
  `_archiv\` alte/ausgemusterte Paare, `erkunden\` Debug-Ausgaben, `browser-profil\` Vinted-Login (nie anfassen).

## Git

- Ins Repo gehören nur Code, Doku und `docs\bilder\`. **Keine persönlichen Daten**: Fotos, `inserate.json`, `statistik.json`,
  `analyse\`, `_archiv\`, `erkunden\` (enthält Vinted-Seiten mit Kontodaten), `browser-profil\` – alles in `.gitignore`.
  Vor jedem Commit `git status` prüfen; neue Ordner mit Nutzerdaten sofort in `.gitignore` aufnehmen.
- README-Screenshots (`docs\bilder\`) stammen aus einer Test-Kopie der Zentrale (eigener Port, Beispiel-Statistik) bzw. einem
  zugeschnittenen Formular-Screenshot ohne Profilbild/Nachrichten. Beim Erneuern genauso vorgehen.
- Commits/Push nur, wenn der Nutzer es möchte.

## Regeln (vom Nutzer so gewollt)

- **Niemals bei Vinted absenden, veröffentlichen, löschen oder Nachrichten schicken.** Skripte füllen nur aus; der Nutzer klickt.
- **Nie Passwörter eingeben**, keine Captchas lösen. Der Nutzer loggt sich selbst ein.
- **Nicht raten:** Marke nur aus lesbarem Text/Logo, Größe nur aus einer gelesenen Zahl. Unsicheres → Marker + Frage.
  Der Nutzer will die Beschreibung **nie von Hand** bearbeiten – Hinweise dürfen nie „Text ändern/[?] löschen“ verlangen.
- **Preise legt der Nutzer fest.** Analyse schreibt nur `preis_vorschlag`; Vinteds Empfehlung ist nur Info.
- **`inserate.json` nie aus einem alten Stand komplett überschreiben** – der Nutzer arbeitet parallel in der Zentrale.
  Nur über `vinted.setze_felder(_mehrere)` (mit Dateisperre `inserate.lock`) oder `werkzeuge\uebernehmen.py` schreiben.
  Bei eigenen Datenkorrekturen: kleines Python-Skript, das frisch liest, gezielt Felder ändert und `vinted.schreibe_inserate` nutzt.
- **Nichts endgültig löschen.** „Löschen“ heißt: nach `_archiv\<datum>_<name>\` verschieben; der Nutzer löscht selbst.
- Vinted-AGB verbieten Automatisierung; der Nutzer hat das Risiko bewusst akzeptiert (kleiner Privatgebrauch) – nicht erneut
  diskutieren, aber schonend arbeiten: ein Inserat nach dem anderen, Mensch klickt ab, 3–6 neue Inserate pro Tag empfehlen,
  Statistik höchstens ~1× täglich.
- Tests an Kopien (eigener Port, z. B. 8790, `chrome_port` auf einen freien Wert), nie destruktiv gegen Port 8765 oder die
  echte `inserate.json`; niemals Aufträge starten, die den echten Vinted-Chrome steuern, ohne dass der Nutzer es will.

## Stolpersteine

- Bash-Heredocs mit Apostrophen (`Levi's`, `Women's`) brechen ab → Python-Skript als Datei schreiben und ausführen.
- PowerShell 5.1 `Set-Content -Encoding UTF8` schreibt ein BOM – Lesecode nutzt `utf-8-sig`.
- `os.replace` scheitert unter Windows, wenn die Zieldatei offen ist → `schreibe_inserate` wiederholt automatisch.
- Fotos öffnen immer über `vinted.oeffne_bild(pfad)` (HEIC + EXIF-Drehung); Upload-Fotos ohne Metadaten (GPS) über `vinted.upload_fotos`.
- Preisfeld der englischen Oberfläche erwartet Punkt als Dezimaltrenner.
