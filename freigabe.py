"""Lokale Freigabe-Seite: Inserate prüfen, bearbeiten und freigeben.

Start: python vinted.py freigabe  (oder Doppelklick auf "Freigabe starten.bat")
Läuft nur auf diesem Rechner (127.0.0.1), nur Python-Standardbibliothek + Pillow.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import vinted

WEB = vinted.BASIS / "web"
VORSCHAU_BREITEN = (360, 1600)
_schreib_lock = threading.Lock()
_fotos_lock = threading.Lock()


class Fehler(Exception):
    def __init__(self, status: HTTPStatus, text: str, extra: dict | None = None):
        super().__init__(text)
        self.status = status
        self.text = text
        self.extra = extra or {}


def lese(config: dict) -> list[dict]:
    try:
        return vinted.lese_inserate(config)
    except vinted.DateiFehler as e:
        raise Fehler(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))


def version(config: dict) -> int:
    pfad = vinted.inserate_pfad(config)
    return pfad.stat().st_mtime_ns if pfad.exists() else 0


def sicherer_bildpfad(config: dict, ordner: str, datei: str) -> Path:
    wurzel = vinted.artikel_wurzel(config).resolve()
    pfad = (wurzel / ordner / datei).resolve()
    if pfad.parent.parent != wurzel or not pfad.is_file() or pfad.suffix.lower() not in vinted.BILD_ENDUNGEN:
        raise Fehler(HTTPStatus.NOT_FOUND, "Bild nicht gefunden")
    return pfad


def vorschau(config: dict, ordner: str, datei: str, breite: int) -> Path:
    quelle = sicherer_bildpfad(config, ordner, datei)
    breite = min(VORSCHAU_BREITEN, key=lambda b: abs(b - breite))
    cache = quelle.parent / "_vorschau" / f"{quelle.name}_{breite}.jpg"
    stand = quelle.stat().st_mtime_ns
    if not cache.exists() or cache.stat().st_mtime_ns != stand:
        cache.parent.mkdir(exist_ok=True)
        im = vinted.oeffne_bild(quelle)
        im.thumbnail((breite, breite))
        tmp = cache.with_name(cache.name + f".{threading.get_ident()}.tmp")
        im.save(tmp, "JPEG", quality=82)
        os.utime(tmp, ns=(stand, stand))
        try:
            os.replace(tmp, cache)
        except PermissionError:  # gleichzeitig von einer zweiten Anfrage erzeugt
            os.remove(tmp)
    return cache


def ergaenze(config: dict, inserat: dict) -> dict:
    """Felder für die Seite: vorhandene Fotos, fehlender Ordner, nicht mehr vorhandene Fotos."""
    alle = vinted.bilder_im_ordner(config, inserat["ordner"])
    echt = {f.lower(): f for f in alle}
    gewaehlt = inserat.get("fotos") or []
    inserat["_alle_fotos"] = alle
    inserat["_fotos_fehlen"] = [f for f in gewaehlt if f.lower() not in echt]
    inserat["fotos"] = list(dict.fromkeys(echt[f.lower()] for f in gewaehlt if f.lower() in echt))
    inserat["_ordner_fehlt"] = not (vinted.artikel_wurzel(config) / inserat["ordner"]).is_dir()
    return inserat


def alle_daten(config: dict) -> dict:
    """Inserate aus inserate.json, ergänzt um Ordner, für die es noch kein Inserat gibt."""
    with _schreib_lock:
        inserate = lese(config)
        stand = version(config)
    vorhanden = {i["ordner"] for i in inserate}
    wurzel = vinted.artikel_wurzel(config)
    if wurzel.is_dir():
        for d in sorted(wurzel.iterdir()):
            if d.is_dir() and not d.name.startswith((".", "_")) and d.name not in vorhanden:
                inserate.append(vinted.leeres_inserat(config, d.name))
    for i in inserate:
        ergaenze(config, i)
    inserate.sort(key=lambda i: i["ordner"])
    return {
        "inserate": inserate,
        "version": stand,
        "status": vinted.STATUS,
        "zustaende": vinted.ZUSTAENDE,
        "pakete": vinted.PAKETE,
        "domain": config["domain"],
    }


def als_zahl(feld: str, wert):
    if wert in (None, ""):
        return None
    text = str(wert).replace("€", "").replace(" ", "").strip()
    if text.endswith((",-", ".-")):
        text = text[:-2]
    try:
        zahl = round(float(text.replace(",", ".")), 2)
    except ValueError:
        raise Fehler(HTTPStatus.BAD_REQUEST, f"{feld}: keine Zahl")
    if zahl != zahl or zahl in (float("inf"), float("-inf")) or zahl < 0:
        raise Fehler(HTTPStatus.BAD_REQUEST, f"{feld}: keine gültige Zahl")
    return zahl


def bereinige(config: dict, ordner: str, aenderungen: dict) -> dict:
    sauber = {}
    for feld, wert in aenderungen.items():
        if feld in vinted.TEXTFELDER:
            sauber[feld] = "" if wert is None else str(wert)
        elif feld in vinted.ZAHLFELDER:
            sauber[feld] = als_zahl(feld, wert)
        elif feld == "status":
            if wert not in vinted.STATUS:
                raise Fehler(HTTPStatus.BAD_REQUEST, f"Unbekannter Status: {wert}")
            sauber[feld] = wert
        elif feld == "fotos":
            if not isinstance(wert, list) or not all(isinstance(f, str) for f in wert):
                raise Fehler(HTTPStatus.BAD_REQUEST, "Ungültige Fotoliste")
            echt = {f.lower(): f for f in vinted.bilder_im_ordner(config, ordner)}
            sauber[feld] = list(dict.fromkeys(echt[f.lower()] for f in wert if f.lower() in echt))
        else:
            raise Fehler(HTTPStatus.BAD_REQUEST, f"Unbekanntes Feld: {feld}")
    return sauber


def aendere_inserat(config: dict, ordner: str, aenderungen: dict, basis: dict) -> dict:
    """Ändert nur die übergebenen Felder. `basis` sind die Werte, von denen die Seite
    ausging: Hat jemand anderes (z. B. Claude) ein Feld inzwischen geändert, gibt es 409
    statt eines stillen Überschreibens."""
    if not (vinted.artikel_wurzel(config) / ordner).is_dir() and not any(
            i["ordner"] == ordner for i in lese(config)):
        raise Fehler(HTTPStatus.NOT_FOUND, "Ordner nicht gefunden")
    sauber = bereinige(config, ordner, aenderungen)
    with _schreib_lock, vinted.datei_sperre(config):
        inserate = lese(config)
        inserat = next((i for i in inserate if i["ordner"] == ordner), None)
        if inserat is None:
            inserat = vinted.leeres_inserat(config, ordner)
            inserate.append(inserat)
        gespeichert = ergaenze(config, dict(inserat))  # Fotoliste wie die Seite sie kennt
        konflikt = [f for f, neu in sauber.items()
                    if f in basis and gespeichert.get(f) != basis[f] and gespeichert.get(f) != neu]
        if konflikt:
            raise Fehler(HTTPStatus.CONFLICT, "Inzwischen woanders geändert: " + ", ".join(konflikt),
                         {"konflikt": konflikt, "inserat": ergaenze(config, dict(inserat))})
        inserat.update(sauber)
        inserat["geaendert"] = datetime.now().isoformat(timespec="seconds")
        try:
            vinted.schreibe_inserate(config, inserate)
        except PermissionError:
            raise Fehler(HTTPStatus.CONFLICT, "inserate.json ist gesperrt (in einem anderen Programm offen?)")
        stand = version(config)
    antwort = ergaenze(config, dict(inserat))
    antwort["_version"] = stand
    return antwort


# --- Fragen: unsichere Angaben per Knopf bestätigen statt im Text zu bearbeiten ---------
# Jede Frage in inserat["fragen"] hat Optionen mit Textersetzungen (für Titel und
# Beschreibung) und Feldwerten. "{wert}" steht für eine Eingabe des Nutzers.
TEXT_ZIELE = ("titel", "beschreibung")
ERLAUBTE_FELDER = set(vinted.TEXTFELDER) | set(vinted.ZAHLFELDER)


def _finde_inserat(inserate: list[dict], ordner: str) -> dict:
    inserat = next((i for i in inserate if i["ordner"] == ordner), None)
    if inserat is None:
        raise Fehler(HTTPStatus.NOT_FOUND, "Inserat nicht gefunden")
    return inserat


def beantworte(config: dict, ordner: str, frage_id: str, option: int, wert: str) -> dict:
    wert = (wert or "").strip()
    with _schreib_lock, vinted.datei_sperre(config):
        inserate = lese(config)
        inserat = _finde_inserat(inserate, ordner)
        frage = next((f for f in inserat.get("fragen") or [] if f.get("id") == frage_id), None)
        if frage is None:
            raise Fehler(HTTPStatus.NOT_FOUND, "Frage nicht gefunden")
        if frage.get("antwort"):
            raise Fehler(HTTPStatus.CONFLICT, "Diese Frage ist schon beantwortet")
        try:
            opt = frage["optionen"][int(option)]
        except (IndexError, ValueError, TypeError):
            raise Fehler(HTTPStatus.BAD_REQUEST, "Unbekannte Antwort")
        if opt.get("eingabe") and not wert:
            raise Fehler(HTTPStatus.BAD_REQUEST, "Bitte erst einen Wert eintragen")
        felder = {k: v for k, v in (opt.get("felder") or {}).items() if k in ERLAUBTE_FELDER}
        betroffen = list(TEXT_ZIELE) + [k for k in felder if k not in TEXT_ZIELE]
        vorher = {k: inserat.get(k) for k in betroffen}
        nicht_gefunden = []
        for paar in opt.get("ersetzen") or []:
            alt, neu = paar[0], paar[1].replace("{wert}", wert)
            optional = len(paar) > 2 and paar[2]  # z. B. Hashtag, der nicht immer vorkommt
            treffer = False
            for ziel in TEXT_ZIELE:
                if alt in (inserat.get(ziel) or ""):
                    inserat[ziel] = inserat[ziel].replace(alt, neu)
                    treffer = True
            if not treffer and not optional:
                nicht_gefunden.append(alt)
        for k, v in felder.items():
            v = v.replace("{wert}", wert) if isinstance(v, str) else v
            inserat[k] = bereinige(config, ordner, {k: v})[k]
        frage["antwort"] = opt.get("label", "") + (f": {wert}" if wert else "")
        if nicht_gefunden:
            frage["hinweis"] = "Textstelle nicht gefunden, bitte die Beschreibung kurz prüfen."
        inserat.setdefault("verlauf", []).append(
            {"frage": frage_id, "vorher": vorher, "nachher": {k: inserat.get(k) for k in betroffen}})
        inserat["geaendert"] = datetime.now().isoformat(timespec="seconds")
        vinted.schreibe_inserate(config, inserate)
        stand = version(config)
    antwort = ergaenze(config, dict(inserat))
    antwort["_version"] = stand
    return antwort


def antwort_zurueck(config: dict, ordner: str) -> dict:
    """Macht die zuletzt beantwortete Frage rückgängig, solange die Felder seitdem unverändert sind."""
    with _schreib_lock, vinted.datei_sperre(config):
        inserate = lese(config)
        inserat = _finde_inserat(inserate, ordner)
        verlauf = inserat.get("verlauf") or []
        if not verlauf:
            raise Fehler(HTTPStatus.CONFLICT, "Nichts zum Rückgängigmachen")
        letzter = verlauf[-1]
        geaendert = [k for k, v in letzter["nachher"].items() if inserat.get(k) != v]
        if geaendert:
            raise Fehler(HTTPStatus.CONFLICT, "Seitdem von Hand geändert (" + ", ".join(geaendert) + "), Rückgängig nicht möglich")
        inserat.update(letzter["vorher"])
        verlauf.pop()
        for f in inserat.get("fragen") or []:
            if f.get("id") == letzter["frage"]:
                f.pop("antwort", None)
                f.pop("hinweis", None)
        inserat["geaendert"] = datetime.now().isoformat(timespec="seconds")
        vinted.schreibe_inserate(config, inserate)
        stand = version(config)
    antwort = ergaenze(config, dict(inserat))
    antwort["_version"] = stand
    return antwort


def fotos_bereitstellen(config: dict, ordner: str) -> int:
    if not _fotos_lock.acquire(blocking=False):
        raise Fehler(HTTPStatus.CONFLICT, "Fotos werden gerade schon vorbereitet")
    try:
        inserat = next((i for i in lese(config) if i["ordner"] == ordner), None)
        if inserat is None or not inserat.get("fotos"):
            raise Fehler(HTTPStatus.BAD_REQUEST, "Keine Fotos ausgewählt")
        try:
            pfade = vinted.upload_fotos(config, inserat)
        except FileNotFoundError as e:
            raise Fehler(HTTPStatus.BAD_REQUEST, str(e))
        if hasattr(os, "startfile"):
            os.startfile(str(pfade[0].parent))
        return len(pfade)
    finally:
        _fotos_lock.release()


# --- Aufträge: vinted.py-Befehle aus der Zentrale starten (immer nur einer gleichzeitig) ---

class Auftrag:
    def __init__(self):
        self.proc = None
        self.titel = ""
        self.ordner = None
        self.log: list[str] = []
        self.ende = None
        self.lock = threading.Lock()

    def laeuft(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stand(self) -> dict:
        return {"laeuft": self.laeuft(), "titel": self.titel, "ordner": self.ordner,
                "log": self.log[-40:], "ende": self.ende}


AUFTRAG = Auftrag()
AUFTRAEGE = {  # name -> (Befehl, Titel, braucht Ordner)
    "ausfuellen": (["ausfuellen"], "Inserat in Vinted ausfüllen", True),
    "hochladen": (["hochladen"], "Freigegebene Inserate nacheinander ausfüllen", False),
    "preise": (["preise"], "Vinted-Preisempfehlungen abfragen", False),
    "statistik": (["statistik"], "Aufrufe & Favoriten abrufen", False),
}


def _lies_ausgabe(proc) -> None:
    for zeile in proc.stdout:
        AUFTRAG.log.append(zeile.rstrip())
        del AUFTRAG.log[:-300]
    AUFTRAG.ende = proc.wait()


def starte_auftrag(config: dict, name: str, ordner: str | None) -> dict:
    if name not in AUFTRAEGE:
        raise Fehler(HTTPStatus.BAD_REQUEST, "Unbekannter Auftrag")
    befehl, titel, braucht_ordner = AUFTRAEGE[name]
    with AUFTRAG.lock:
        if AUFTRAG.laeuft():
            raise Fehler(HTTPStatus.CONFLICT, f"Es läuft schon: {AUFTRAG.titel}")
        if not vinted.chrome_laeuft(config):
            raise Fehler(HTTPStatus.CONFLICT, "Der Vinted-Chrome ist nicht offen. Erst oben „Vinted-Chrome öffnen“ und einloggen.")
        args = list(befehl)
        if braucht_ordner:
            if not ordner or not any(i["ordner"] == ordner for i in lese(config)):
                raise Fehler(HTTPStatus.BAD_REQUEST, "Inserat nicht gefunden")
            args.append(ordner)
        elif ordner:
            args += ["--nur", ordner]
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        AUFTRAG.proc = subprocess.Popen(
            [sys.executable, "-u", str(vinted.BASIS / "vinted.py")] + args,
            cwd=str(vinted.BASIS), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"), **kwargs)
        AUFTRAG.titel, AUFTRAG.ordner, AUFTRAG.log, AUFTRAG.ende = titel, ordner, [], None
        threading.Thread(target=_lies_ausgabe, args=(AUFTRAG.proc,), daemon=True).start()
    return AUFTRAG.stand()


def stoppe_auftrag() -> dict:
    with AUFTRAG.lock:
        if AUFTRAG.laeuft():
            AUFTRAG.proc.terminate()
            AUFTRAG.log.append("Abgebrochen. Der Vinted-Tab bleibt offen, gespeichert wurde nichts.")
    return AUFTRAG.stand()


def chrome_oeffnen(config: dict) -> dict:
    if not vinted.chrome_laeuft(config):
        vinted.starte_chrome(config, config["domain"])
    return {"laeuft": True}


class Handler(BaseHTTPRequestHandler):
    config: dict = {}
    erlaubte_hosts: set = set()

    def log_message(self, format, *args):  # Konsole ruhig halten
        pass

    def _antwort(self, status: HTTPStatus, body: bytes, typ: str, kopf: dict | None = None) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (kopf or {"Cache-Control": "no-store"}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except ConnectionError:  # Browser hat abgebrochen (z. B. Bild nicht mehr gebraucht)
            self.close_connection = True

    def _json(self, status: HTTPStatus, daten) -> None:
        self._antwort(status, json.dumps(daten, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _fehler(self, e: Exception) -> None:
        if isinstance(e, Fehler):
            self._json(e.status, dict({"fehler": e.text}, **e.extra))
        elif isinstance(e, TimeoutError):
            self._json(HTTPStatus.CONFLICT, {"fehler": str(e)})
        else:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"fehler": f"{type(e).__name__}: {e}"})

    def _host_ok(self) -> bool:
        # Schutz gegen DNS-Rebinding: nur Aufrufe an 127.0.0.1/localhost
        return self.headers.get("Host", "") in self.erlaubte_hosts

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(HTTPStatus.FORBIDDEN, {"fehler": "Falscher Host"})
        url = urlparse(self.path)
        try:
            if url.path in ("/", "/index.html"):
                html = (WEB / "freigabe.html").read_bytes()
                return self._antwort(HTTPStatus.OK, html, "text/html; charset=utf-8")
            if url.path == "/api/daten":
                return self._json(HTTPStatus.OK, alle_daten(self.config))
            if url.path == "/api/version":
                return self._json(HTTPStatus.OK, {"version": version(self.config)})
            if url.path == "/api/statistik":
                return self._json(HTTPStatus.OK, vinted.lese_statistik(self.config))
            if url.path == "/api/status":
                return self._json(HTTPStatus.OK, {"version": version(self.config),
                                                  "chrome": vinted.chrome_laeuft(self.config),
                                                  "auftrag": AUFTRAG.stand()})
            if url.path.startswith("/bild/"):
                teile = url.path[len("/bild/"):].split("/")
                if len(teile) != 2:
                    raise Fehler(HTTPStatus.NOT_FOUND, "Bild nicht gefunden")
                ordner, datei = (unquote(t) for t in teile)
                try:
                    breite = int(parse_qs(url.query).get("w", ["360"])[0])
                except ValueError:
                    breite = 360
                pfad = vorschau(self.config, ordner, datei, breite)
                st = pfad.stat()
                etag = f'"{st.st_mtime_ns}-{st.st_size}"'
                kopf = {"Cache-Control": "no-cache", "ETag": etag}
                if self.headers.get("If-None-Match") == etag:
                    return self._antwort(HTTPStatus.NOT_MODIFIED, b"", "image/jpeg", kopf)
                return self._antwort(HTTPStatus.OK, pfad.read_bytes(), "image/jpeg", kopf)
            raise Fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        except Exception as e:
            self._fehler(e)

    def do_POST(self) -> None:
        # Nur JSON von der eigenen Seite annehmen (fremde Webseiten können das nicht ohne CORS)
        herkunft = self.headers.get("Origin")
        if not self._host_ok() or (herkunft and herkunft.split("//", 1)[-1] not in self.erlaubte_hosts):
            return self._json(HTTPStatus.FORBIDDEN, {"fehler": "Fremde Herkunft"})
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"fehler": "JSON erwartet"})
        try:
            try:
                laenge = int(self.headers.get("Content-Length", "0"))
                daten = json.loads(self.rfile.read(laenge) or b"{}")
            except (ValueError, UnicodeDecodeError):
                raise Fehler(HTTPStatus.BAD_REQUEST, "Ungültiges JSON in der Anfrage")
            if not isinstance(daten, dict):
                raise Fehler(HTTPStatus.BAD_REQUEST, "Ungültige Anfrage")
            ordner = str(daten.get("ordner", ""))
            if self.path == "/api/inserat":
                aenderungen = daten.get("aenderungen")
                basis = daten.get("basis") or {}
                if not isinstance(aenderungen, dict) or not isinstance(basis, dict):
                    raise Fehler(HTTPStatus.BAD_REQUEST, "aenderungen fehlt")
                return self._json(HTTPStatus.OK, aendere_inserat(self.config, ordner, aenderungen, basis))
            if self.path == "/api/fotos-bereitstellen":
                return self._json(HTTPStatus.OK, {"anzahl": fotos_bereitstellen(self.config, ordner)})
            if self.path == "/api/antwort":
                return self._json(HTTPStatus.OK, beantworte(self.config, ordner, str(daten.get("frage", "")),
                                                            daten.get("option"), str(daten.get("wert") or "")))
            if self.path == "/api/antwort-zurueck":
                return self._json(HTTPStatus.OK, antwort_zurueck(self.config, ordner))
            if self.path == "/api/auftrag":
                return self._json(HTTPStatus.OK, starte_auftrag(self.config, str(daten.get("name", "")), ordner or None))
            if self.path == "/api/auftrag-stoppen":
                return self._json(HTTPStatus.OK, stoppe_auftrag())
            if self.path == "/api/chrome-oeffnen":
                return self._json(HTTPStatus.OK, chrome_oeffnen(self.config))
            raise Fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        except Exception as e:
            self._fehler(e)


class Server(ThreadingHTTPServer):
    # Unter Windows würde SO_REUSEADDR einen zweiten Server auf denselben Port lassen
    allow_reuse_address = False
    daemon_threads = True


def starte(config: dict, browser_oeffnen: bool = True) -> None:
    port = int(config.get("freigabe_port", 8765))
    url = f"http://127.0.0.1:{port}/"
    try:
        server = Server(("127.0.0.1", port), Handler)
    except OSError:
        try:
            with urllib.request.urlopen(url + "api/version", timeout=2):
                pass
            print(f"Die Freigabe-Seite läuft schon: {url}")
            if browser_oeffnen:
                webbrowser.open(url)
            return
        except OSError:
            raise SystemExit(f"Port {port} ist von einem anderen Programm belegt. "
                             f"In config.json 'freigabe_port' ändern.")
    Handler.config = config
    Handler.erlaubte_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    print(f"Freigabe-Seite läuft: {url}  (Beenden: Fenster schließen oder Strg+C)", flush=True)
    if browser_oeffnen:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
