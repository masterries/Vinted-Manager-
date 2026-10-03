"""Language of the hub's messages (setting "ui_language": "en" or "de").

Source texts in the code are English and go through tr():
    tr("Photo missing: {files}", files="a.jpg")
The German translation of each text lives in DE below (same {placeholders}).
Texts stored in the listings (questions, hints, title, description ...) are never translated.
Check that every tr() text has a German entry: scratchpad script check_i18n_py.py.
"""
from __future__ import annotations

import os
import time

LANGUAGES = ("en", "de")
CACHE_SECONDS = 2  # read the settings again at least this often (catches in-place rewrites within one tick)

DE = {
    # --- field names (messages in the hub, job log) ---
    "Title": "Titel",
    "Description": "Beschreibung",
    "Category": "Kategorie",
    "Brand": "Marke",
    "Size": "Größe",
    "Condition": "Zustand",
    "Colour": "Farbe",
    "Material": "Material",
    "Heel height": "Absatzhöhe",
    "Shape": "Schuhform",
    "Package size": "Paketgröße",
    "Package size ({size})": "Paketgröße ({size})",
    "Note": "Notiz",
    "Price": "Preis",
    "Minimum price": "Mindestpreis",
    "Photos": "Fotos",
    "Status": "Status",

    # --- core.py ---
    "{name} is broken (line {line}, column {column}): {error}":
        "{name} ist fehlerhaft (Zeile {line}, Spalte {column}): {error}",
    "{name} is not saved as UTF-8": "{name} ist nicht als UTF-8 gespeichert",
    "{name} is locked by another program right now": "{name} ist gerade von einem anderen Programm gesperrt",
    "Photo folder missing: {folder}": "Foto-Ordner fehlt: {folder}",
    "Photo missing: {files}": "Foto fehlt: {files}",
    "No photos selected": "Keine Fotos ausgewählt",
    "Invalid settings": "Ungültige Einstellungen",
    "Unknown setting: {key}": "Unbekannte Einstellung: {key}",
    "Invalid value for {key}: {value} (allowed: {allowed})": "Ungültiger Wert für {key}: {value} (erlaubt: {allowed})",

    # --- server.py ---
    "Image not found": "Bild nicht gefunden",
    "changes missing": "changes fehlt",
    "settings.json is locked (open in another program?)":
        "settings.json ist gesperrt (in einem anderen Programm offen?)",
    "{field}: not a number": "{field}: keine Zahl",
    "{field}: not a valid number": "{field}: keine gültige Zahl",
    "Unknown status: {status}": "Unbekannter Status: {status}",
    "Invalid photo list": "Ungültige Fotoliste",
    "Unknown field: {field}": "Unbekanntes Feld: {field}",
    "Folder not found": "Ordner nicht gefunden",
    "Changed elsewhere in the meantime: {fields}": "Inzwischen woanders geändert: {fields}",
    "listings.json is locked (open in another program?)":
        "listings.json ist gesperrt (in einem anderen Programm offen?)",
    "Listing not found": "Inserat nicht gefunden",
    "Question not found": "Frage nicht gefunden",
    "This question is already answered": "Diese Frage ist schon beantwortet",
    "Unknown answer": "Unbekannte Antwort",
    "Please enter a value first": "Bitte erst einen Wert eintragen",
    "Text not found, please check the description.": "Textstelle nicht gefunden, bitte die Beschreibung kurz prüfen.",
    "Nothing to undo": "Nichts zum Rückgängigmachen",
    "Changed by hand since then ({fields}), cannot undo":
        "Seitdem von Hand geändert ({fields}), Rückgängig nicht möglich",
    "Photos are already being prepared": "Fotos werden gerade schon vorbereitet",
    "Fill listing into Vinted": "Inserat in Vinted ausfüllen",
    "Fill approved listings one after another": "Freigegebene Inserate nacheinander ausfüllen",
    "Get Vinted price recommendations": "Vinted-Preisempfehlungen abfragen",
    "Fetch views & favourites": "Aufrufe & Favoriten abrufen",
    "Unknown job": "Unbekannter Auftrag",
    "Already running: {title}": "Es läuft schon: {title}",
    "The Vinted Chrome is not open. Open it at the top first and log in.":
        "Der Vinted-Chrome ist nicht offen. Erst oben „Vinted-Chrome öffnen“ und einloggen.",
    "Stopped. The Vinted tab stays open, nothing was saved.":
        "Abgebrochen. Der Vinted-Tab bleibt offen, gespeichert wurde nichts.",
    "Wrong host": "Falscher Host",
    "Not found": "Nicht gefunden",
    "Foreign origin": "Fremde Herkunft",
    "JSON expected": "JSON erwartet",
    "Invalid JSON in the request": "Ungültiges JSON in der Anfrage",
    "Invalid request": "Ungültige Anfrage",
    "The hub is already running: {url}": "Die Zentrale läuft schon: {url}",
    "Port {port} is used by another program. Change 'hub_port' in config.json.":
        "Port {port} ist von einem anderen Programm belegt. In config.json 'hub_port' ändern.",
    "Vinted Hub is running: {url}  (to stop: close this window or press Ctrl+C)":
        "Vinted Zentrale läuft: {url}  (Beenden: Fenster schließen oder Strg+C)",

    # --- chrome.py ---
    "Google Chrome not found.": "Google Chrome nicht gefunden.",
    "Chrome does not respond on the debug port.": "Chrome reagiert nicht auf dem Debug-Port.",

    # --- form.py (job log: what was filled in / what is missing) ---
    "Upload form not found. Are you logged in to the Vinted Chrome? (Vinted Login.bat)":
        "Upload-Formular nicht gefunden. Bist du im Vinted-Chrome eingeloggt? (Vinted Login.bat)",
    "{count} photos": "{count} Fotos",
    "Check photos (not all previews appeared)": "Fotos prüfen (nicht alle Vorschauen erschienen)",
    "Category ({category})": "Kategorie ({category})",
    "Brand (choose '{label}' on Vinted)": "Marke (bei Vinted '{label}' wählen)",
    "Brand ({brand} not in the list)": "Marke ({brand} nicht in der Liste)",
    "Brand ({brand})": "Marke ({brand})",
    "Brand (unknown)": "Marke (unbekannt)",
    "Size ({size} not found)": "Größe ({size} nicht gefunden)",
    "Size ({size})": "Größe ({size})",
    "Size (unknown)": "Größe (unbekannt)",
    "Condition ({condition})": "Zustand ({condition})",
    "Colour ({colors})": "Farbe ({colors})",

    # --- commands.py (job log) ---
    "The Vinted Chrome is already open. Just log in there.": "Der Vinted-Chrome ist schon offen. Dort einfach einloggen.",
    "Chrome is open (own profile, separate from your normal Chrome).":
        "Chrome ist offen (eigenes Profil, getrennt von deinem normalen Chrome).",
    "Please log in to Vinted yourself as usual. The window may stay open.":
        "Bitte bei Vinted ganz normal selbst einloggen. Das Fenster darf offen bleiben.",
    "Not logged in (or upload form not found). First open the Vinted Chrome and log in (Vinted Login.bat)":
        "Nicht eingeloggt (oder Upload-Formular nicht gefunden). Erst den Vinted-Chrome öffnen und einloggen "
        "(Vinted Login.bat)",
    "{count} elements saved in {folder}": "{count} Elemente gespeichert in {folder}",
    "Filled in: {fields}": "Ausgefüllt: {fields}",
    "Please add by hand: {fields}": "Bitte von Hand ergänzen: {fields}",
    "Vinted price recommendation: {bargain} / {optimal} / {premium} € (bargain / optimal / premium), "
    "your price: {price} €":
        "Vinted-Preisempfehlung: {bargain} / {optimal} / {premium} € (günstig / optimal / premium), "
        "dein Preis: {price} €",
    "Careful: the text still contains [?] placeholders, replace them before submitting!":
        "Achtung: Im Text stehen noch [?]-Platzhalter, vor dem Absenden ersetzen!",
    "No listing for folder {folder}": "Kein Inserat für Ordner {folder}",
    "Now check the Chrome window and click 'Save draft' or 'Upload' yourself.":
        "Jetzt im Chrome-Fenster prüfen und selbst auf 'Save draft' oder 'Upload' klicken.",
    "✓ Created on Vinted: {url}": "✓ Bei Vinted angelegt: {url}",
    "Tab closed, nothing saved.": "Tab geschlossen, nichts gespeichert.",
    "Own Vinted profile ID not found. Are you logged in to the Vinted Chrome?":
        "Eigene Vinted-Profil-ID nicht gefunden. Bist du im Vinted-Chrome eingeloggt?",
    "Vinted refused the request (status {status}). Try again later.":
        "Vinted hat die Abfrage abgelehnt (Status {status}). Später nochmal versuchen.",
    "{count} items on Vinted, {matched} of them matched to listings in the hub.":
        "{count} Artikel bei Vinted, {matched} davon Inseraten der Zentrale zugeordnet.",
    "{views:4} views{views_plus:7}  {favorites:3} fav.{favorites_plus:6}  {title}":
        "{views:4} Aufrufe{views_plus:7}  {favorites:3} Fav.{favorites_plus:6}  {title}",
    "No matching listings (they need a category and must not be on Vinted yet).":
        "Keine passenden Inserate (brauchen eine Kategorie und dürfen noch nicht bei Vinted sein).",
    "(without: {fields})": "(ohne: {fields})",
    "No recommendation found": "Keine Empfehlung gefunden",
    "(missing: {fields})": "(fehlt: {fields})",
    "Error: {error}": "Fehler: {error}",
    "Done.": "Fertig.",
    "No approved listings. Approve them in the hub first.": "Keine freigegebenen Inserate. Erst in der Zentrale freigeben.",
    "Check and click 'Save draft' or 'Upload' yourself. The script waits until then.":
        "Prüfen und selbst auf 'Save draft' oder 'Upload' klicken. Das Skript wartet so lange.",
    "Tab closed, upload stopped.": "Tab geschlossen, Upload beendet.",
    "✓ Online on Vinted: {url}": "✓ Online bei Vinted: {url}",
    "✓ Saved as a draft on Vinted: {url}": "✓ Als Entwurf bei Vinted gespeichert: {url}",
    "Could not check yet whether it is online - 'Fetch statistics' updates the status later.":
        "Konnte noch nicht prüfen, ob es online ist – „Statistik abrufen“ gleicht den Status später ab.",
    "All approved listings are created on Vinted.": "Alle freigegebenen Inserate sind bei Vinted angelegt.",

    # --- __main__.py (CLI) ---
    "Use: settings set key=value ...": "Aufruf: settings set schlüssel=wert ...",
    "Use: settings set key=value ... (keys: {keys})": "Aufruf: settings set schlüssel=wert ... (Schlüssel: {keys})",
    "Expected key=value, got: {text}": "Erwartet schlüssel=wert, bekommen: {text}",
}

# Cached language, refreshed when config.json or data/settings.json change on disk, and at the latest after
# CACHE_SECONDS: file times on Windows only tick about every 15.6 ms, so a same-size rewrite in place within one
# tick would otherwise keep the old language until the next change
_cache: dict = {"key": None, "path": None, "lang": "en", "at": 0.0}


def _stamp(path):
    """Changes whenever the file is rewritten (settings are saved via a temp file + replace)."""
    if path is None:
        return None
    try:
        st = os.stat(path)
    except OSError:
        return "missing"
    return (st.st_mtime_ns, st.st_size, st.st_ino)


def language() -> str:
    """The current UI language ("en" or "de"), read lazily from the settings."""
    from . import core  # here, not at the top: core imports this module
    config_file = core.ROOT / "config.json"
    old_path = _cache["path"]
    # stamps taken before reading: a change while reading makes the next call read again
    key = (_stamp(config_file), _stamp(old_path))
    now = time.monotonic()
    if old_path is None or key != _cache["key"] or now - _cache["at"] > CACHE_SECONDS:
        try:
            config = core.load_config()
            path = core.settings_path(config)
            lang = config.get("ui_language")
        except Exception:  # broken config.json: messages in English, the real error shows elsewhere
            path, lang = None, "en"
        if path != old_path:  # first call (or other data folder): no stamp yet, read again next time
            key = None
        _cache.update(key=key, path=path, lang=lang if lang in LANGUAGES else "en", at=now)
    return _cache["lang"]


def forget_language() -> None:
    """Read the language again on the next tr() (called after saving the settings)."""
    _cache.update(key=None, path=None)


def tr(source: str, /, **kw) -> str:
    """Translate an English source text into the UI language, then fill in {placeholders}
    (positional-only, so a placeholder may be called {source} or {text} too)."""
    text = DE.get(source, source) if language() == "de" else source
    return text.format(**kw) if kw else text
