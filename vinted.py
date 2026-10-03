"""Halbautomatischer Vinted-Upload für viele Inserate (z. B. Schuhe).

Ablauf:
  1. python vinted.py login      -> Chrome öffnet sich, du loggst dich selbst ein, Fenster schließen
  2. Fotos pro Artikel in schuhe/<ordner>/ legen, Claude füllt inserate.json
  3. python vinted.py freigabe   -> lokale Seite: Inserate prüfen, bearbeiten, freigeben
  4. python vinted.py hochladen  -> legt freigegebene Inserate als Entwurf bei Vinted an

Die Inserate werden nie automatisch veröffentlicht. Du schaust die Entwürfe
bei Vinted an und klickst selbst auf "Hochladen".
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

BASIS = Path(__file__).resolve().parent
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
try:  # iPhone-Fotos (HEIC) lesen können
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    BILD_ENDUNGEN -= {".heic", ".heif"}

STATUS = ["neu", "freigegeben", "entwurf", "online", "verkauft", "zurueckgestellt"]
ZUSTAENDE = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut", "Zufriedenstellend"]
PAKETE = ["Klein", "Mittel", "Groß"]
TEXTFELDER = ["titel", "beschreibung", "kategorie", "marke", "groesse", "zustand",
              "farbe", "material", "absatzhoehe", "schuhform", "paket", "notiz"]
ZAHLFELDER = ["preis", "preis_min"]


def lade_config() -> dict:
    with open(BASIS / "config.json", encoding="utf-8-sig") as f:
        return json.load(f)


def artikel_wurzel(config: dict) -> Path:
    return BASIS / config["schuhe_ordner"]


# --- inserate.json -------------------------------------------------------------

class DateiFehler(Exception):
    """inserate.json lässt sich nicht lesen (z. B. von Hand kaputt bearbeitet)."""


def inserate_pfad(config: dict) -> Path:
    return BASIS / config["inserate_datei"]


def lese_inserate(config: dict) -> list[dict]:
    pfad = inserate_pfad(config)
    if not pfad.exists():
        return []
    try:
        return json.loads(pfad.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise DateiFehler(f"{pfad.name} ist fehlerhaft (Zeile {e.lineno}, Spalte {e.colno}): {e.msg}")
    except UnicodeDecodeError:
        raise DateiFehler(f"{pfad.name} ist nicht als UTF-8 gespeichert")


def schreibe_inserate(config: dict, inserate: list[dict]) -> None:
    """Sicher schreiben: eindeutige Temp-Datei, auf Platte bringen, eine Sicherung (.bak)
    behalten und dann ersetzen. Kurz wiederholen, falls Windows die Datei gerade sperrt."""
    pfad = inserate_pfad(config)
    fd, tmp = tempfile.mkstemp(dir=pfad.parent, prefix=pfad.stem + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(inserate, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        if pfad.exists():
            shutil.copy2(pfad, pfad.with_name(pfad.name + ".bak"))
        for versuch in range(10):
            try:
                os.replace(tmp, pfad)
                return
            except PermissionError:
                if versuch == 9:
                    raise
                time.sleep(0.05 * (versuch + 1))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class datei_sperre:
    """Sperre über Prozessgrenzen hinweg (Zentrale + Upload-/Statistik-Skript schreiben dieselbe Datei)."""

    def __init__(self, config: dict):
        self.pfad = inserate_pfad(config).with_suffix(".lock")
        self.datei = None

    def __enter__(self):
        self.datei = open(self.pfad, "a+")
        for _ in range(200):  # bis zu ca. 10 Sekunden warten
            try:
                if os.name == "nt":
                    import msvcrt
                    self.datei.seek(0)
                    msvcrt.locking(self.datei.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.datei.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                time.sleep(0.05)
        self.datei.close()
        raise TimeoutError("inserate.json ist gerade von einem anderen Programm gesperrt")

    def __exit__(self, *args):
        try:
            if os.name == "nt":
                import msvcrt
                self.datei.seek(0)
                msvcrt.locking(self.datei.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.datei.fileno(), fcntl.LOCK_UN)
        finally:
            self.datei.close()


def setze_felder_mehrere(config: dict, aenderungen: dict) -> None:
    """Felder mehrerer Inserate in einem Schritt ändern: {ordner: {feld: wert}}."""
    from datetime import datetime
    if not aenderungen:
        return
    with datei_sperre(config):
        inserate = lese_inserate(config)
        for i in inserate:
            if i["ordner"] in aenderungen:
                i.update(aenderungen[i["ordner"]])
                i["geaendert"] = datetime.now().isoformat(timespec="seconds")
        schreibe_inserate(config, inserate)


def setze_felder(config: dict, ordner: str, felder: dict) -> None:
    """Einzelne Felder eines Inserats ändern, alles andere unverändert lassen."""
    setze_felder_mehrere(config, {ordner: felder})


def bilder_im_ordner(config: dict, ordner: str) -> list[str]:
    """Dateinamen aller Originalfotos eines Artikels (ohne _upload/_vorschau)."""
    d = artikel_wurzel(config) / ordner
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file() and f.suffix.lower() in BILD_ENDUNGEN)


def leeres_inserat(config: dict, ordner: str) -> dict:
    inserat = {"ordner": ordner, "status": "neu", "fotos": bilder_im_ordner(config, ordner), "hinweise": []}
    for feld in TEXTFELDER:
        inserat[feld] = ""
    for feld in ZAHLFELDER:
        inserat[feld] = None
    return inserat


def oeffne_bild(pfad: Path):
    from PIL import Image, ImageOps
    im = Image.open(pfad)
    return ImageOps.exif_transpose(im).convert("RGB")


def upload_fotos(config: dict, inserat: dict) -> list[Path]:
    """Schreibt die gewählten Fotos als _upload/01.jpg, 02.jpg, ... in der gewählten
    Reihenfolge: gedreht, verkleinert und ohne Metadaten (GPS)."""
    basis = artikel_wurzel(config) / inserat["ordner"]
    if not basis.is_dir():
        raise FileNotFoundError(f"Foto-Ordner fehlt: {inserat['ordner']}")
    namen = inserat.get("fotos", [])[: config["max_fotos"]]
    fehlend = [n for n in namen if not (basis / n).is_file()]
    if not namen or fehlend:
        raise FileNotFoundError("Foto fehlt: " + ", ".join(fehlend) if fehlend else "Keine Fotos ausgewählt")
    aus = basis / "_upload"
    aus.mkdir(exist_ok=True)
    for alt in aus.glob("*.jpg"):
        alt.unlink()
    pfade = []
    for i, name in enumerate(namen, start=1):
        im = oeffne_bild(basis / name)
        im.thumbnail((2000, 2000))
        ziel = aus / f"{i:02d}.jpg"
        # ohne exif= gespeichert -> keine GPS-/Kamera-Metadaten im Upload
        im.save(ziel, "JPEG", quality=90)
        pfade.append(ziel)
    return pfade


# --- Browser ------------------------------------------------------------------
# Chrome wird ganz normal gestartet (nicht von Playwright), damit du dich selbst
# einloggen kannst. Das Upload-Skript verbindet sich danach über den lokalen
# Debug-Port mit diesem Fenster.

def chrome_pfad() -> str:
    kandidaten = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for k in kandidaten:
        if k.is_file():
            return str(k)
    raise SystemExit("Google Chrome nicht gefunden.")


def cdp_url(config: dict) -> str:
    return f"http://127.0.0.1:{config.get('chrome_port', 9222)}"


def chrome_laeuft(config: dict) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(cdp_url(config) + "/json/version", timeout=1):
            return True
    except OSError:
        return False


def starte_chrome(config: dict, url: str) -> None:
    import subprocess
    subprocess.Popen([
        chrome_pfad(),
        f"--user-data-dir={BASIS / config['profil_ordner']}",
        f"--remote-debugging-port={config.get('chrome_port', 9222)}",
        "--no-first-run", "--no-default-browser-check",
        url,
    ])


def verbinde_chrome(p, config: dict):
    """Verbindet sich mit dem Vinted-Chrome (startet ihn, falls er nicht offen ist)."""
    import time
    if not chrome_laeuft(config):
        starte_chrome(config, config["domain"])
        for _ in range(30):
            time.sleep(0.5)
            if chrome_laeuft(config):
                break
        else:
            raise SystemExit("Chrome reagiert nicht auf dem Debug-Port.")
    browser = p.chromium.connect_over_cdp(cdp_url(config))
    return browser, browser.contexts[0]


def ist_eingeloggt(page, config: dict) -> bool:
    page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    if "/items/new" not in page.url:
        return False
    return page.locator("input[type=file]").count() > 0


# --- login ------------------------------------------------------------------

def befehl_login(config: dict) -> None:
    if chrome_laeuft(config):
        print("Der Vinted-Chrome ist schon offen. Dort einfach einloggen.")
        return
    starte_chrome(config, config["domain"])
    print("Chrome ist offen (eigenes Profil, getrennt von deinem normalen Chrome).")
    print("Bitte bei Vinted ganz normal selbst einloggen. Das Fenster darf offen bleiben.")


# --- erkunden (Formular auslesen, um Selektoren zu bauen) ----------------------

FORMULAR_JS = """
() => {
  const out = [];
  const sel = '[data-testid], input, textarea, select, button, [role="button"], [role="combobox"], [role="listbox"]';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    out.push({
      tag: el.tagName.toLowerCase(),
      testid: el.getAttribute('data-testid'),
      id: el.id || null,
      name: el.getAttribute('name'),
      type: el.getAttribute('type'),
      placeholder: el.getAttribute('placeholder'),
      aria: el.getAttribute('aria-label'),
      role: el.getAttribute('role'),
      text: (el.innerText || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 100),
      sichtbar: r.width > 0 && r.height > 0,
    });
  }
  return out;
}
"""


def befehl_erkunden(config: dict) -> None:
    from playwright.sync_api import sync_playwright

    ziel = BASIS / "erkunden"
    ziel.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser, ctx = verbinde_chrome(p, config)
        page = ctx.new_page()
        try:
            if not ist_eingeloggt(page, config):
                page.screenshot(path=str(ziel / "nicht_eingeloggt.png"), full_page=True)
                raise SystemExit("Nicht eingeloggt (oder Upload-Formular nicht gefunden). Erst: python vinted.py login")
            page.wait_for_timeout(2000)
            elemente = page.evaluate(FORMULAR_JS)
            (ziel / "formular.json").write_text(json.dumps(elemente, ensure_ascii=False, indent=1), encoding="utf-8")
            (ziel / "formular.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(ziel / "formular.png"), full_page=True)
            print(f"{len(elemente)} Elemente gespeichert in {ziel}")
        finally:
            page.close()


# --- hochladen ----------------------------------------------------------------

# Selektoren des Vinted-Formulars (Stand Oktober 2026, englische Oberfläche auf vinted.lu).
# Ändert Vinted das Formular, zeigt "python vinted.py erkunden" die neuen Namen.
SEL_FOTOS = "[data-testid=add-photos-input], input[type=file]"
SEL_FOTO_VORSCHAU = "[data-testid^=image-wrapper-]"
SEL_TITEL = "[data-testid=title--input]"
SEL_BESCHREIBUNG = "[data-testid=description--input]"
SEL_PREIS = "[data-testid=price-input--input]"
SEL_MARKE_SUCHE = "#brand-search-input"
SEL_COOKIES_ABLEHNEN = "#onetrust-reject-all-handler"
# Auswahllisten: "<name>-input" öffnet, "<name>-content" enthält die Optionen
DD_KATEGORIE = "catalog-select-dropdown"
DD_MARKE = "brand-select-dropdown"
DD_GROESSE = "category-size-single-grid"
DD_ZUSTAND = "category-condition-single-list"
DD_FARBE = "color-select-dropdown"
DD_MATERIAL = "category-material-multi-list"

ZUSTAND_EN = {"Neu mit Etikett": "New with tags", "Neu ohne Etikett": "New without tags",
              "Sehr gut": "Very good", "Gut": "Good", "Zufriedenstellend": "Satisfactory"}
FARBE_EN = {"schwarz": "Black", "grau": "Grey", "weiß": "White", "weiss": "White", "creme": "Cream",
            "beige": "Beige", "orange": "Orange", "rot": "Red", "bordeaux": "Burgundy", "pink": "Pink",
            "rosa": "Pink", "lila": "Purple", "violett": "Purple", "blau": "Blue", "navy": "Navy",
            "türkis": "Turquoise", "grün": "Green", "khaki": "Khaki", "gelb": "Yellow", "gold": "Gold",
            "silber": "Silver", "braun": "Brown", "cognac": "Brown", "mehrfarbig": "Multi"}
MATERIAL_EN = {"leder": "Leather", "wildleder": "Suede", "kunstleder": "Faux leather",
               "canvas": "Canvas", "gummi": "Rubber", "jute": "Jute"}


# Vinted zeigt nach Kategorie/Marke/Zustand/Preis eine Preisempfehlung (Bargain/Optimal/Premium)
PREIS_JS = r"""
() => {
  const t = document.body.innerText;
  const i = t.indexOf('Price recommendation');
  if (i < 0) return null;
  const teil = t.slice(i, i + 400), out = {};
  const re = /€\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(Bargain|Optimal|Premium)/g;
  let m;
  while ((m = re.exec(teil))) out[m[2].toLowerCase()] = parseFloat(m[1].replace(',', '.'));
  return Object.keys(out).length ? out : null;
}
"""


def lies_preisempfehlung(page) -> dict | None:
    from datetime import date
    for _ in range(12):
        try:
            emp = page.evaluate(PREIS_JS)
        except Exception:
            emp = None
        if emp:
            return {"guenstig": emp.get("bargain"), "optimal": emp.get("optimal"),
                    "premium": emp.get("premium"), "datum": date.today().isoformat()}
        page.wait_for_timeout(500)
    return None


OPTIONEN = "[role=radio], [role=checkbox], [role=button]"


def _option(bereich, text: str, warte_ms: int = 5000):
    """Option, deren erste Textzeile genau `text` ist (Vinted zeigt darunter oft eine Erklärung).
    Gibt None zurück, wenn es keine gibt."""
    kandidaten = bereich.locator(OPTIONEN)
    js = """(els, t) => els.findIndex(e =>
        (e.innerText || '').trim().split('\\n')[0].trim().toLowerCase() === t.toLowerCase())"""
    for _ in range(max(1, warte_ms // 250)):
        idx = kandidaten.evaluate_all(js, text)
        if idx >= 0:
            return kandidaten.nth(idx)
        bereich.page.wait_for_timeout(250)
    return None


def _oeffne(page, name: str):
    page.locator(f"[data-testid={name}-input]").first.click()
    inhalt = page.locator(f"[data-testid={name}-content]").first
    inhalt.wait_for(state="visible", timeout=6000)
    return inhalt


def _schliesse(page, name: str) -> None:
    """Offene Auswahlliste schließen: Escape, notfalls Klick auf die Überschrift der Seite."""
    inhalt = page.locator(f"[data-testid={name}-content]").first
    for versuch in (lambda: page.keyboard.press("Escape"), lambda: page.locator("h1").first.click()):
        if not inhalt.is_visible():
            return
        try:
            versuch()
        except Exception:
            pass
        page.wait_for_timeout(400)


def _waehle(page, name: str, werte: list[str]) -> list[str]:
    """Wählt Optionen in einer Auswahlliste. Gibt die nicht gefundenen Werte zurück."""
    inhalt = _oeffne(page, name)
    fehlend = []
    for wert in werte:
        opt = _option(inhalt, wert, warte_ms=2500)
        if opt is not None:
            opt.scroll_into_view_if_needed()
            opt.click()
            page.wait_for_timeout(500)
        else:
            fehlend.append(wert)
    if fehlend:  # zur Fehlersuche festhalten, welche Optionen es gab
        texte = inhalt.locator(OPTIONEN).all_inner_texts()
        (BASIS / "erkunden").mkdir(exist_ok=True)
        (BASIS / "erkunden" / f"optionen_{name}.txt").write_text("\n".join(texte), encoding="utf-8")
    _schliesse(page, name)
    return fehlend


def _bekannt(wert) -> bool:
    w = str(wert or "").strip().lower()
    return bool(w) and w not in ("unbekannt", "unklar", "?", "[?]")


def fuelle_formular(page, config: dict, inserat: dict, nur_details: bool = False) -> tuple[list[str], list[str]]:
    """Füllt das Vinted-Formular aus (ohne zu speichern). Gibt (erledigt, offen) zurück.
    nur_details=True: nur Kategorie, Marke, Größe und Zustand (für die Preisempfehlung)."""
    erledigt, offen = [], []
    page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
    try:
        page.locator(SEL_TITEL).first.wait_for(state="visible", timeout=20000)
    except Exception:
        raise SystemExit("Upload-Formular nicht gefunden. Bist du im Vinted-Chrome eingeloggt? (Vinted Login.bat)")
    if page.locator(SEL_COOKIES_ABLEHNEN).is_visible():
        page.locator(SEL_COOKIES_ABLEHNEN).click()

    def text(sel, wert, name):
        try:
            feld = page.locator(sel).first
            feld.fill(wert)
            page.wait_for_timeout(300)
            erledigt.append(name)
        except Exception:
            offen.append(name)

    if not nur_details:
        # Fotos: alle auf einmal, in der Reihenfolge der Zentrale
        fotos = upload_fotos(config, inserat)
        page.locator(SEL_FOTOS).first.set_input_files([str(f) for f in fotos])
        try:
            page.wait_for_function("([sel, n]) => document.querySelectorAll(sel).length >= n",
                                   arg=[SEL_FOTO_VORSCHAU, len(fotos)], timeout=90000)
            erledigt.append(f"{len(fotos)} Fotos")
        except Exception:
            offen.append("Fotos prüfen (nicht alle Vorschauen erschienen)")
        text(SEL_TITEL, inserat.get("titel", ""), "Titel")
        text(SEL_BESCHREIBUNG, inserat.get("beschreibung", ""), "Beschreibung")

    # Kategorie: Pfad wie "Women > Shoes > Boots > Ankle boots"
    pfad = [t.strip() for t in str(inserat.get("kategorie", "")).split(">") if t.strip()]
    try:
        inhalt = _oeffne(page, DD_KATEGORIE)
        for teil in pfad:
            opt = _option(inhalt, teil)
            if opt is None:
                raise LookupError(teil)
            opt.scroll_into_view_if_needed()
            opt.click()
            page.wait_for_timeout(800)
        page.locator(f"[data-testid={DD_MARKE}-input]").first.wait_for(state="visible", timeout=8000)
        erledigt.append("Kategorie")
    except Exception:
        _schliesse(page, DD_KATEGORIE)
        offen.append(f"Kategorie ({inserat.get('kategorie')})")
        return erledigt, offen + ["Marke", "Größe", "Zustand", "Farbe", "Preis"]

    # Marke über das Suchfeld
    marke = inserat.get("marke", "")
    if str(marke).strip().lower() in ("ohne marke", "keine marke", "no brand"):
        offen.append("Marke (ohne Marke: bei Vinted leer lassen oder passend wählen)")
    elif _bekannt(marke):
        try:
            inhalt = _oeffne(page, DD_MARKE)
            page.locator(SEL_MARKE_SUCHE).first.press_sequentially(marke, delay=60)
            page.wait_for_timeout(1500)
            treffer = _option(inhalt, marke, warte_ms=3000)
            if treffer is not None:
                treffer.click()
                page.wait_for_timeout(500)
                erledigt.append("Marke")
            else:
                _schliesse(page, DD_MARKE)
                offen.append(f"Marke ({marke} nicht in der Liste)")
        except Exception:
            offen.append(f"Marke ({marke})")
    else:
        offen.append("Marke (unbekannt)")

    groesse = str(inserat.get("groesse", "")).strip()
    if _bekannt(groesse):
        try:
            if _waehle(page, DD_GROESSE, [groesse]):
                offen.append(f"Größe ({groesse} nicht gefunden)")
            else:
                erledigt.append("Größe")
        except Exception:
            offen.append(f"Größe ({groesse})")
    else:
        offen.append("Größe (unbekannt)")

    zustand = ZUSTAND_EN.get(inserat.get("zustand", ""))
    if zustand:
        try:
            if _waehle(page, DD_ZUSTAND, [zustand]):
                offen.append(f"Zustand ({zustand})")
            else:
                erledigt.append("Zustand")
        except Exception:
            offen.append(f"Zustand ({zustand})")
    else:
        offen.append("Zustand")

    if nur_details:
        return erledigt, offen

    farben = [FARBE_EN.get(f.strip().lower()) for f in str(inserat.get("farbe", "")).split(",") if f.strip()]
    farben = [f for f in dict.fromkeys(farben) if f][:2]
    if farben:
        try:
            fehlend = _waehle(page, DD_FARBE, farben)
            if fehlend:
                offen.append("Farbe (" + ", ".join(fehlend) + ")")
            else:
                erledigt.append("Farbe")
        except Exception:
            offen.append("Farbe")
    else:
        offen.append("Farbe")

    # Material nur, wenn es nicht als "vermutlich" markiert ist (optional bei Vinted)
    material = str(inserat.get("material", "")).strip().lower()
    if material and "vermutlich" not in material and material in MATERIAL_EN:
        try:
            if not _waehle(page, DD_MATERIAL, [MATERIAL_EN[material]]):
                erledigt.append("Material")
        except Exception:
            pass

    preis = inserat.get("preis")
    text(SEL_PREIS, ("%g" % preis) if preis else "", "Preis")
    # Paketgröße: Vinted wählt selbst eine Empfehlung vor
    return erledigt, offen


def _melde(inserat: dict, erledigt: list[str], offen: list[str], empfehlung: dict | None) -> None:
    print("  Ausgefüllt:", ", ".join(erledigt) or "-")
    if offen:
        print("  Bitte von Hand ergänzen:", ", ".join(offen))
    if empfehlung:
        print(f"  Vinted-Preisempfehlung: {empfehlung['guenstig']} / {empfehlung['optimal']} / "
              f"{empfehlung['premium']} € (günstig / optimal / premium), dein Preis: {inserat.get('preis')} €")
    if "[?" in inserat.get("titel", "") + inserat.get("beschreibung", ""):
        print("  Achtung: Im Text stehen noch [?]-Platzhalter, vor dem Absenden ersetzen!")


def _fuellen_und_merken(page, config: dict, inserat: dict) -> None:
    erledigt, offen = fuelle_formular(page, config, inserat)
    empfehlung = lies_preisempfehlung(page) if "Kategorie" in erledigt else None
    if empfehlung:
        setze_felder(config, inserat["ordner"], {"vinted_preis": empfehlung})
    _melde(inserat, erledigt, offen, empfehlung)


def _warte_auf_absenden(page) -> bool:
    """Wartet, bis du gespeichert/hochgeladen hast (Seite verlässt /items/new). False = Tab geschlossen."""
    try:
        page.wait_for_url(lambda url: "/items/new" not in url, timeout=0)
        return True
    except Exception:
        return False


def befehl_ausfuellen(config: dict, ordner: str) -> None:
    """Ein einzelnes Inserat ausfüllen (egal welcher Status), Absenden machst du selbst."""
    from playwright.sync_api import sync_playwright

    inserat = next((i for i in lese_inserate(config) if i["ordner"] == ordner), None)
    if inserat is None:
        raise SystemExit(f"Kein Inserat für Ordner {ordner}")
    with sync_playwright() as p:
        browser, ctx = verbinde_chrome(p, config)
        page = ctx.new_page()
        page.bring_to_front()
        print(f"{inserat['titel']}")
        _fuellen_und_merken(page, config, inserat)
        (BASIS / "erkunden").mkdir(exist_ok=True)
        page.screenshot(path=str(BASIS / "erkunden" / f"ausgefuellt_{ordner}.png"), full_page=True)
        print("  Jetzt im Chrome-Fenster prüfen und selbst auf 'Save draft' oder 'Upload' klicken.", flush=True)
        if _warte_auf_absenden(page):
            setze_felder(config, ordner, {"status": "entwurf", "vinted_url": page.url})
            print("  ✓ Bei Vinted angelegt:", page.url)
        else:
            print("  Tab geschlossen, nichts gespeichert.")


# --- statistik: Aufrufe und Favoriten der eigenen Inserate (nur lesen) ----------

def statistik_pfad(config: dict) -> Path:
    return BASIS / config.get("statistik_datei", "statistik.json")


def lese_statistik(config: dict) -> dict:
    pfad = statistik_pfad(config)
    if not pfad.exists():
        return {"mitglied_id": None, "verlauf": []}
    return json.loads(pfad.read_text(encoding="utf-8-sig"))


def schreibe_statistik(config: dict, daten: dict) -> None:
    pfad = statistik_pfad(config)
    fd, tmp = tempfile.mkstemp(dir=pfad.parent, prefix=pfad.stem + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(daten, ensure_ascii=False, indent=1))
    os.replace(tmp, pfad)


def _normal(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _mitglied_id(page, config: dict, inserate: list[dict], stand: dict) -> str:
    import re
    if stand.get("mitglied_id"):
        return str(stand["mitglied_id"])
    for i in inserate:
        m = re.search(r"/member/(\d+)", i.get("vinted_url") or "")
        if m:
            return m.group(1)
    page.goto(config["domain"], wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for href in page.eval_on_selector_all("a[href*='/member/']", "els => els.map(e => e.getAttribute('href'))"):
        m = re.search(r"/member/(\d+)", href or "")
        if m:
            return m.group(1)
    raise SystemExit("Eigene Vinted-Profil-ID nicht gefunden. Bist du im Vinted-Chrome eingeloggt?")


def _lade_garderobe(page, config: dict, mitglied: str) -> list[dict]:
    """Alle eigenen Artikel über dieselbe Abfrage, die dein Vinted-Profil beim Öffnen macht."""
    page.goto(f"{config['domain']}/member/{mitglied}", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    artikel, seite = [], 1
    while True:
        antwort = page.evaluate("""async (url) => {
            const r = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
            return {status: r.status, text: await r.text()};
        }""", f"/api/v2/wardrobe/{mitglied}/items?page={seite}&per_page=96&order=relevance")
        if antwort["status"] != 200:
            raise SystemExit(f"Vinted hat die Abfrage abgelehnt (Status {antwort['status']}). Später nochmal versuchen.")
        daten = json.loads(antwort["text"])
        artikel += daten.get("items") or []
        if seite >= ((daten.get("pagination") or {}).get("total_pages") or 1):
            return artikel
        seite += 1
        page.wait_for_timeout(1500)


def befehl_statistik(config: dict) -> None:
    import difflib
    from datetime import datetime
    from playwright.sync_api import sync_playwright

    stand = lese_statistik(config)
    inserate = lese_inserate(config)
    with sync_playwright() as p:
        browser, ctx = verbinde_chrome(p, config)
        page = ctx.new_page()
        try:
            mitglied = _mitglied_id(page, config, inserate, stand)
            roh = _lade_garderobe(page, config, mitglied)
        finally:
            page.close()

    jetzt = datetime.now().isoformat(timespec="seconds")
    artikel = [{
        "id": a["id"], "titel": a.get("title", ""), "url": a.get("url") or (config["domain"] + (a.get("path") or "")),
        "preis": float((a.get("price") or {}).get("amount") or 0), "aufrufe": a.get("view_count") or 0,
        "favoriten": a.get("favourite_count") or 0, "entwurf": bool(a.get("is_draft")), "verkauft": bool(a.get("is_closed")),
        "reserviert": bool(a.get("is_reserved")), "versteckt": bool(a.get("is_hidden")),
    } for a in roh]
    vorher = {a["id"]: a for a in (stand["verlauf"][-1]["artikel"] if stand.get("verlauf") else [])}
    stand["mitglied_id"] = mitglied
    stand.setdefault("verlauf", []).append({"zeit": jetzt, "artikel": artikel})
    schreibe_statistik(config, stand)

    # Vinted-Artikel den Inseraten der Zentrale zuordnen: erst über die ID, dann über den Titel
    offen = [i for i in inserate if not i.get("vinted_id")]
    aenderungen, zugeordnet = {}, 0
    for a in artikel:
        inserat = next((i for i in inserate if i.get("vinted_id") == a["id"]), None)
        if inserat is None:
            inserat = next((i for i in offen if _normal(i.get("titel")) == _normal(a["titel"])), None)
        if inserat is None and offen:
            bester = max(offen, key=lambda i: difflib.SequenceMatcher(None, _normal(i.get("titel")), _normal(a["titel"])).ratio())
            if difflib.SequenceMatcher(None, _normal(bester.get("titel")), _normal(a["titel"])).ratio() >= 0.8:
                inserat = bester
        if inserat is None:
            continue
        if inserat in offen:
            offen.remove(inserat)
        zugeordnet += 1
        alt = vorher.get(a["id"], {})
        felder = {"vinted_id": a["id"], "vinted_url": a["url"],
                  "vinted_stats": {"aufrufe": a["aufrufe"], "favoriten": a["favoriten"], "zeit": jetzt,
                                   "aufrufe_vorher": alt.get("aufrufe"), "favoriten_vorher": alt.get("favoriten"),
                                   "preis": a["preis"]}}
        status = inserat.get("status")
        if a["verkauft"] and status in ("freigegeben", "entwurf", "online"):
            felder["status"] = "verkauft"
        elif a["entwurf"] and status in ("freigegeben", "online"):
            felder["status"] = "entwurf"
        elif not a["entwurf"] and not a["verkauft"] and status in ("freigegeben", "entwurf"):
            felder["status"] = "online"
        aenderungen[inserat["ordner"]] = felder
    setze_felder_mehrere(config, aenderungen)

    print(f"{len(artikel)} Artikel bei Vinted, {zugeordnet} davon Inseraten der Zentrale zugeordnet.")
    for a in sorted(artikel, key=lambda x: -x["aufrufe"]):
        alt = vorher.get(a["id"], {})
        plus = lambda neu, k: f" (+{neu - alt[k]})" if k in alt and neu > alt[k] else ""
        print(f"  {a['aufrufe']:4} Aufrufe{plus(a['aufrufe'], 'aufrufe'):7}  {a['favoriten']:3} Fav.{plus(a['favoriten'], 'favoriten'):6}  {a['titel'][:55]}")


def befehl_preise(config: dict, nur: str | None) -> None:
    """Liest Vinteds Preisempfehlung für noch nicht eingestellte Inserate aus.
    Füllt dafür nur Kategorie, Marke, Größe und Zustand aus und speichert nichts bei Vinted."""
    import random
    from playwright.sync_api import sync_playwright

    inserate = [i for i in lese_inserate(config)
                if i.get("status") in ("neu", "zurueckgestellt", "freigegeben") and i.get("kategorie")
                and (not nur or i["ordner"] == nur)]
    if not inserate:
        print("Keine passenden Inserate (brauchen eine Kategorie und dürfen noch nicht bei Vinted sein).")
        return
    with sync_playwright() as p:
        browser, ctx = verbinde_chrome(p, config)
        for n, inserat in enumerate(inserate, start=1):
            print(f"[{n}/{len(inserate)}] {inserat['titel']}", flush=True)
            page = ctx.new_page()
            try:
                erledigt, offen = fuelle_formular(page, config, inserat, nur_details=True)
                empfehlung = None
                if "Kategorie" in erledigt:
                    empfehlung = lies_preisempfehlung(page)
                    vorschlag = inserat.get("preis") or inserat.get("preis_vorschlag")
                    if not empfehlung and vorschlag:  # manchmal erst nach einer Preiseingabe sichtbar
                        page.locator(SEL_PREIS).first.fill("%g" % vorschlag)
                        empfehlung = lies_preisempfehlung(page)
                if empfehlung:
                    setze_felder(config, inserat["ordner"], {"vinted_preis": empfehlung})
                    print(f"  Vinted: {empfehlung['guenstig']} / {empfehlung['optimal']} / {empfehlung['premium']} €"
                          + (f"  (ohne: {', '.join(offen)})" if offen else ""), flush=True)
                else:
                    print("  Keine Empfehlung gefunden" + (f" (fehlt: {', '.join(offen)})" if offen else ""), flush=True)
            except Exception as e:
                print(f"  Fehler: {e}", flush=True)
            finally:
                page.close(run_before_unload=False)  # Formular verwerfen, nichts speichern
            if n < len(inserate):
                time.sleep(random.uniform(3, 7))
    print("Fertig.")


def befehl_hochladen(config: dict, nur: str | None) -> None:
    from playwright.sync_api import sync_playwright

    inserate = [i for i in lese_inserate(config)
                if i.get("status") == "freigegeben" and (not nur or i["ordner"] == nur)]
    if not inserate:
        print("Keine freigegebenen Inserate. Erst auf der Freigabe-Seite freigeben.")
        return
    with sync_playwright() as p:
        browser, ctx = verbinde_chrome(p, config)
        page = ctx.new_page()
        page.bring_to_front()
        for n, inserat in enumerate(inserate, start=1):
            print(f"\n[{n}/{len(inserate)}] {inserat['titel']}")
            _fuellen_und_merken(page, config, inserat)
            print("  Prüfen und selbst auf 'Save draft' oder 'Upload' klicken. Das Skript wartet so lange.", flush=True)
            if not _warte_auf_absenden(page):
                print("Tab geschlossen, Upload beendet.")
                return
            setze_felder(config, inserat["ordner"], {"status": "entwurf", "vinted_url": page.url})
            print("  ✓ Bei Vinted angelegt. Falls direkt veröffentlicht: in der Zentrale 'Ist online' klicken.")
        page.close()
    print("\nAlle freigegebenen Inserate sind bei Vinted angelegt.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Halbautomatischer Vinted-Upload")
    sub = parser.add_subparsers(dest="befehl", required=True)
    sub.add_parser("login", help="Chrome öffnen und selbst bei Vinted einloggen")
    sub.add_parser("erkunden", help="Upload-Formular auslesen (für die Entwicklung)")
    f = sub.add_parser("freigabe", help="lokale Seite zum Prüfen und Freigeben öffnen")
    f.add_argument("--kein-browser", action="store_true", help="Seite nicht automatisch öffnen")
    a = sub.add_parser("ausfuellen", help="ein Inserat im Vinted-Formular ausfüllen (Absenden machst du)")
    a.add_argument("ordner", help="Ordnername, z. B. 01_espadrilles_keil_pink")
    h = sub.add_parser("hochladen", help="freigegebene Inserate nacheinander ausfüllen")
    h.add_argument("--nur", help="nur diesen Ordner hochladen (zum Testen)")
    pr = sub.add_parser("preise", help="Vinteds Preisempfehlung auslesen (speichert nichts bei Vinted)")
    pr.add_argument("--nur", help="nur diesen Ordner")
    sub.add_parser("statistik", help="Aufrufe und Favoriten der eigenen Inserate abrufen und speichern")
    args = parser.parse_args()

    config = lade_config()
    if args.befehl == "login":
        befehl_login(config)
    elif args.befehl == "erkunden":
        befehl_erkunden(config)
    elif args.befehl == "freigabe":
        import freigabe
        freigabe.starte(config, browser_oeffnen=not args.kein_browser)
    elif args.befehl == "ausfuellen":
        befehl_ausfuellen(config, args.ordner)
    elif args.befehl == "hochladen":
        befehl_hochladen(config, args.nur)
    elif args.befehl == "preise":
        befehl_preise(config, args.nur)
    elif args.befehl == "statistik":
        befehl_statistik(config)


if __name__ == "__main__":
    main()
