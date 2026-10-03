"""Local web hub: review listings, answer questions, prices, approval, jobs, stats.

Start: python -m vinted_hub serve  (or double-click "Start Hub.bat")
Runs only on this machine (127.0.0.1), Python standard library + Pillow only.
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

from . import chrome, core

WEB = Path(__file__).resolve().parent / "web"
PREVIEW_WIDTHS = (360, 1600)
_write_lock = threading.Lock()
_photos_lock = threading.Lock()


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, text: str, extra: dict | None = None):
        super().__init__(text)
        self.status = status
        self.text = text
        self.extra = extra or {}


def read(config: dict) -> list[dict]:
    try:
        return core.read_listings(config)
    except core.DataFileError as e:
        raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))


def version(config: dict) -> int:
    path = core.listings_path(config)
    return path.stat().st_mtime_ns if path.exists() else 0


def safe_image_path(config: dict, folder: str, file: str) -> Path:
    root = core.items_dir(config).resolve()
    path = (root / folder / file).resolve()
    if path.parent.parent != root or not path.is_file() or path.suffix.lower() not in core.IMAGE_EXTENSIONS:
        raise ApiError(HTTPStatus.NOT_FOUND, "Bild nicht gefunden")
    return path


def preview(config: dict, folder: str, file: str, width: int) -> Path:
    source = safe_image_path(config, folder, file)
    width = min(PREVIEW_WIDTHS, key=lambda w: abs(w - width))
    cache = source.parent / "_preview" / f"{source.name}_{width}.jpg"
    mtime = source.stat().st_mtime_ns
    if not cache.exists() or cache.stat().st_mtime_ns != mtime:
        cache.parent.mkdir(exist_ok=True)
        im = core.open_image(source)
        im.thumbnail((width, width))
        tmp = cache.with_name(cache.name + f".{threading.get_ident()}.tmp")
        im.save(tmp, "JPEG", quality=82)
        os.utime(tmp, ns=(mtime, mtime))
        try:
            os.replace(tmp, cache)
        except PermissionError:  # created concurrently by a second request
            os.remove(tmp)
    return cache


def enrich(config: dict, listing: dict) -> dict:
    """Fields for the page: available photos, missing folder, photos that no longer exist."""
    all_photos = core.photos_in_folder(config, listing["folder"])
    actual = {f.lower(): f for f in all_photos}
    chosen = listing.get("photos") or []
    listing["_all_photos"] = all_photos
    listing["_missing_photos"] = [f for f in chosen if f.lower() not in actual]
    listing["photos"] = list(dict.fromkeys(actual[f.lower()] for f in chosen if f.lower() in actual))
    listing["_folder_missing"] = not (core.items_dir(config) / listing["folder"]).is_dir()
    return listing


def all_data(config: dict) -> dict:
    """Listings from listings.json, plus folders that have no listing yet."""
    with _write_lock:
        listings = read(config)
        ver = version(config)
    existing = {i["folder"] for i in listings}
    root = core.items_dir(config)
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if d.is_dir() and not d.name.startswith((".", "_")) and d.name not in existing:
                listings.append(core.empty_listing(config, d.name))
    for i in listings:
        enrich(config, i)
    listings.sort(key=lambda i: i["folder"])
    return {
        "listings": listings,
        "version": ver,
        "statuses": core.STATUSES,
        "conditions": core.CONDITIONS,
        "packages": core.PACKAGES,
        "domain": config["domain"],
    }


# German field names for messages shown in the hub
FIELD_LABELS = {"title": "Titel", "description": "Beschreibung", "category": "Kategorie", "brand": "Marke",
                "size": "Größe", "condition": "Zustand", "color": "Farbe", "material": "Material",
                "heel_height": "Absatzhöhe", "shape": "Schuhform", "package": "Paketgröße", "notes": "Notiz",
                "price": "Preis", "min_price": "Mindestpreis", "photos": "Fotos", "status": "Status"}


def label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def to_number(field: str, value):
    if value in (None, ""):
        return None
    text = str(value).replace("€", "").replace(" ", "").strip()
    if text.endswith((",-", ".-")):
        text = text[:-2]
    try:
        number = round(float(text.replace(",", ".")), 2)
    except ValueError:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{label(field)}: keine Zahl")
    if number != number or number in (float("inf"), float("-inf")) or number < 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{label(field)}: keine gültige Zahl")
    return number


def sanitize(config: dict, folder: str, changes: dict) -> dict:
    clean = {}
    for field, value in changes.items():
        if field in core.TEXT_FIELDS:
            clean[field] = "" if value is None else str(value)
        elif field in core.NUMBER_FIELDS:
            clean[field] = to_number(field, value)
        elif field == "status":
            if value not in core.STATUSES:
                raise ApiError(HTTPStatus.BAD_REQUEST, f"Unbekannter Status: {value}")
            clean[field] = value
        elif field == "photos":
            if not isinstance(value, list) or not all(isinstance(f, str) for f in value):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Ungültige Fotoliste")
            actual = {f.lower(): f for f in core.photos_in_folder(config, folder)}
            clean[field] = list(dict.fromkeys(actual[f.lower()] for f in value if f.lower() in actual))
        else:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"Unbekanntes Feld: {field}")
    return clean


def update_listing(config: dict, folder: str, changes: dict, base: dict) -> dict:
    """Changes only the given fields. `base` holds the values the page started from:
    if someone else (e.g. Claude) changed a field meanwhile, return 409 instead of
    silently overwriting."""
    if not (core.items_dir(config) / folder).is_dir() and not any(
            i["folder"] == folder for i in read(config)):
        raise ApiError(HTTPStatus.NOT_FOUND, "Ordner nicht gefunden")
    clean = sanitize(config, folder, changes)
    with _write_lock, core.file_lock(config):
        listings = read(config)
        listing = next((i for i in listings if i["folder"] == folder), None)
        if listing is None:
            listing = core.empty_listing(config, folder)
            listings.append(listing)
        stored = enrich(config, dict(listing))  # photo list as the page knows it
        conflicts = [f for f, new in clean.items()
                     if f in base and stored.get(f) != base[f] and stored.get(f) != new]
        if conflicts:
            raise ApiError(HTTPStatus.CONFLICT, "Inzwischen woanders geändert: " + ", ".join(conflicts),
                           {"conflicts": conflicts, "listing": enrich(config, dict(listing))})
        listing.update(clean)
        listing["updated_at"] = datetime.now().isoformat(timespec="seconds")
        try:
            core.write_listings(config, listings)
        except PermissionError:
            raise ApiError(HTTPStatus.CONFLICT, "listings.json ist gesperrt (in einem anderen Programm offen?)")
        ver = version(config)
    result = enrich(config, dict(listing))
    result["_version"] = ver
    return result


# --- Questions: confirm uncertain details by button instead of editing the text ---------
# Each question in listing["questions"] has options with text replacements (for title and
# description) and field values. "{value}" stands for user input.
TEXT_TARGETS = ("title", "description")
ALLOWED_FIELDS = set(core.TEXT_FIELDS) | set(core.NUMBER_FIELDS)


def _find_listing(listings: list[dict], folder: str) -> dict:
    listing = next((i for i in listings if i["folder"] == folder), None)
    if listing is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Inserat nicht gefunden")
    return listing


def answer_question(config: dict, folder: str, question_id: str, option: int, value: str) -> dict:
    value = (value or "").strip()
    with _write_lock, core.file_lock(config):
        listings = read(config)
        listing = _find_listing(listings, folder)
        question = next((q for q in listing.get("questions") or [] if q.get("id") == question_id), None)
        if question is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "Frage nicht gefunden")
        if question.get("answer"):
            raise ApiError(HTTPStatus.CONFLICT, "Diese Frage ist schon beantwortet")
        try:
            opt = question["options"][int(option)]
        except (IndexError, ValueError, TypeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Unbekannte Antwort")
        if opt.get("input") and not value:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Bitte erst einen Wert eintragen")
        fields = {k: v for k, v in (opt.get("fields") or {}).items() if k in ALLOWED_FIELDS}
        affected = list(TEXT_TARGETS) + [k for k in fields if k not in TEXT_TARGETS]
        before = {k: listing.get(k) for k in affected}
        not_found = []
        for pair in opt.get("replace") or []:
            old, new = pair[0], pair[1].replace("{value}", value)
            optional = len(pair) > 2 and pair[2]  # e.g. a hashtag that is not always present
            hit = False
            for target in TEXT_TARGETS:
                if old in (listing.get(target) or ""):
                    listing[target] = listing[target].replace(old, new)
                    hit = True
            if not hit and not optional:
                not_found.append(old)
        for k, v in fields.items():
            v = v.replace("{value}", value) if isinstance(v, str) else v
            listing[k] = sanitize(config, folder, {k: v})[k]
        question["answer"] = opt.get("label", "") + (f": {value}" if value else "")
        if not_found:
            question["note"] = "Textstelle nicht gefunden, bitte die Beschreibung kurz prüfen."
        listing.setdefault("history", []).append(
            {"question": question_id, "before": before, "after": {k: listing.get(k) for k in affected}})
        listing["updated_at"] = datetime.now().isoformat(timespec="seconds")
        core.write_listings(config, listings)
        ver = version(config)
    result = enrich(config, dict(listing))
    result["_version"] = ver
    return result


def undo_answer(config: dict, folder: str) -> dict:
    """Undoes the last answered question, as long as its fields are unchanged since."""
    with _write_lock, core.file_lock(config):
        listings = read(config)
        listing = _find_listing(listings, folder)
        history = listing.get("history") or []
        if not history:
            raise ApiError(HTTPStatus.CONFLICT, "Nichts zum Rückgängigmachen")
        last = history[-1]
        changed = [k for k, v in last["after"].items() if listing.get(k) != v]
        if changed:
            raise ApiError(HTTPStatus.CONFLICT, "Seitdem von Hand geändert (" + ", ".join(label(c) for c in changed) + "), Rückgängig nicht möglich")
        listing.update(last["before"])
        history.pop()
        for q in listing.get("questions") or []:
            if q.get("id") == last["question"]:
                q.pop("answer", None)
                q.pop("note", None)
        listing["updated_at"] = datetime.now().isoformat(timespec="seconds")
        core.write_listings(config, listings)
        ver = version(config)
    result = enrich(config, dict(listing))
    result["_version"] = ver
    return result


def prepare_photos(config: dict, folder: str) -> int:
    if not _photos_lock.acquire(blocking=False):
        raise ApiError(HTTPStatus.CONFLICT, "Fotos werden gerade schon vorbereitet")
    try:
        listing = next((i for i in read(config) if i["folder"] == folder), None)
        if listing is None or not listing.get("photos"):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Keine Fotos ausgewählt")
        try:
            paths = core.prepare_upload_photos(config, listing)
        except FileNotFoundError as e:
            raise ApiError(HTTPStatus.BAD_REQUEST, str(e))
        if hasattr(os, "startfile"):
            os.startfile(str(paths[0].parent))
        return len(paths)
    finally:
        _photos_lock.release()


# --- Jobs: run vinted_hub commands from the hub (only one at a time) ---

class Job:
    def __init__(self):
        self.proc = None
        self.title = ""
        self.folder = None
        self.log: list[str] = []
        self.exit_code = None
        self.lock = threading.Lock()

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def status(self) -> dict:
        return {"running": self.running(), "title": self.title, "folder": self.folder,
                "log": self.log[-40:], "exit_code": self.exit_code}


JOB = Job()
JOBS = {  # name -> (command, title, needs folder)
    "fill": (["fill"], "Inserat in Vinted ausfüllen", True),
    "fill_approved": (["fill-approved"], "Freigegebene Inserate nacheinander ausfüllen", False),
    "prices": (["prices"], "Vinted-Preisempfehlungen abfragen", False),
    "stats": (["stats"], "Aufrufe & Favoriten abrufen", False),
}


def _read_output(proc) -> None:
    for line in proc.stdout:
        JOB.log.append(line.rstrip())
        del JOB.log[:-300]
    JOB.exit_code = proc.wait()


def start_job(config: dict, name: str, folder: str | None) -> dict:
    if name not in JOBS:
        raise ApiError(HTTPStatus.BAD_REQUEST, "Unbekannter Auftrag")
    command, title, needs_folder = JOBS[name]
    with JOB.lock:
        if JOB.running():
            raise ApiError(HTTPStatus.CONFLICT, f"Es läuft schon: {JOB.title}")
        if not chrome.chrome_running(config):
            raise ApiError(HTTPStatus.CONFLICT, "Der Vinted-Chrome ist nicht offen. Erst oben „Vinted-Chrome öffnen“ und einloggen.")
        args = list(command)
        if needs_folder:
            if not folder or not any(i["folder"] == folder for i in read(config)):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Inserat nicht gefunden")
            args.append(folder)
        elif folder:
            args += ["--only", folder]
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        JOB.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "vinted_hub"] + args,
            cwd=str(core.ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"), **kwargs)
        JOB.title, JOB.folder, JOB.log, JOB.exit_code = title, folder, [], None
        threading.Thread(target=_read_output, args=(JOB.proc,), daemon=True).start()
    return JOB.status()


def stop_job() -> dict:
    with JOB.lock:
        if JOB.running():
            JOB.proc.terminate()
            JOB.log.append("Abgebrochen. Der Vinted-Tab bleibt offen, gespeichert wurde nichts.")
    return JOB.status()


def open_chrome(config: dict) -> dict:
    if not chrome.chrome_running(config):
        chrome.start_chrome(config, config["domain"])
    return {"running": True}


class Handler(BaseHTTPRequestHandler):
    config: dict = {}
    allowed_hosts: set = set()

    def log_message(self, format, *args):  # keep the console quiet
        pass

    def _respond(self, status: HTTPStatus, body: bytes, content_type: str, headers: dict | None = None) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {"Cache-Control": "no-store"}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except ConnectionError:  # browser aborted (e.g. image no longer needed)
            self.close_connection = True

    def _json(self, status: HTTPStatus, data) -> None:
        self._respond(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, e: Exception) -> None:
        if isinstance(e, ApiError):
            self._json(e.status, dict({"error": e.text}, **e.extra))
        elif isinstance(e, TimeoutError):
            self._json(HTTPStatus.CONFLICT, {"error": str(e)})
        else:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(e).__name__}: {e}"})

    def _host_ok(self) -> bool:
        # DNS rebinding protection: only requests to 127.0.0.1/localhost
        return self.headers.get("Host", "") in self.allowed_hosts

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Falscher Host"})
        url = urlparse(self.path)
        try:
            if url.path in ("/", "/index.html"):
                html = (WEB / "hub.html").read_bytes()
                return self._respond(HTTPStatus.OK, html, "text/html; charset=utf-8")
            if url.path == "/api/data":
                return self._json(HTTPStatus.OK, all_data(self.config))
            if url.path == "/api/version":
                return self._json(HTTPStatus.OK, {"version": version(self.config)})
            if url.path == "/api/stats":
                return self._json(HTTPStatus.OK, core.read_stats(self.config))
            if url.path == "/api/status":
                return self._json(HTTPStatus.OK, {"version": version(self.config),
                                                  "chrome": chrome.chrome_running(self.config),
                                                  "job": JOB.status()})
            if url.path.startswith("/image/"):
                parts = url.path[len("/image/"):].split("/")
                if len(parts) != 2:
                    raise ApiError(HTTPStatus.NOT_FOUND, "Bild nicht gefunden")
                folder, file = (unquote(p) for p in parts)
                try:
                    width = int(parse_qs(url.query).get("w", ["360"])[0])
                except ValueError:
                    width = 360
                path = preview(self.config, folder, file, width)
                st = path.stat()
                etag = f'"{st.st_mtime_ns}-{st.st_size}"'
                headers = {"Cache-Control": "no-cache", "ETag": etag}
                if self.headers.get("If-None-Match") == etag:
                    return self._respond(HTTPStatus.NOT_MODIFIED, b"", "image/jpeg", headers)
                return self._respond(HTTPStatus.OK, path.read_bytes(), "image/jpeg", headers)
            raise ApiError(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        except Exception as e:
            self._error(e)

    def do_POST(self) -> None:
        # Only accept JSON from our own page (foreign sites cannot send it without CORS)
        origin = self.headers.get("Origin")
        if not self._host_ok() or (origin and origin.split("//", 1)[-1] not in self.allowed_hosts):
            return self._json(HTTPStatus.FORBIDDEN, {"error": "Fremde Herkunft"})
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JSON erwartet"})
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, UnicodeDecodeError):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Ungültiges JSON in der Anfrage")
            if not isinstance(data, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Ungültige Anfrage")
            folder = str(data.get("folder", ""))
            if self.path == "/api/listing":
                changes = data.get("changes")
                base = data.get("base") or {}
                if not isinstance(changes, dict) or not isinstance(base, dict):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "changes fehlt")
                return self._json(HTTPStatus.OK, update_listing(self.config, folder, changes, base))
            if self.path == "/api/photos/prepare":
                return self._json(HTTPStatus.OK, {"count": prepare_photos(self.config, folder)})
            if self.path == "/api/answer":
                return self._json(HTTPStatus.OK, answer_question(self.config, folder, str(data.get("question", "")),
                                                                 data.get("option"), str(data.get("value") or "")))
            if self.path == "/api/answer/undo":
                return self._json(HTTPStatus.OK, undo_answer(self.config, folder))
            if self.path == "/api/job":
                return self._json(HTTPStatus.OK, start_job(self.config, str(data.get("name", "")), folder or None))
            if self.path == "/api/job/stop":
                return self._json(HTTPStatus.OK, stop_job())
            if self.path == "/api/chrome/open":
                return self._json(HTTPStatus.OK, open_chrome(self.config))
            raise ApiError(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        except Exception as e:
            self._error(e)


class Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR would allow a second server on the same port
    allow_reuse_address = False
    daemon_threads = True


def run(config: dict, open_browser: bool = True) -> None:
    port = int(config.get("hub_port", 8765))
    url = f"http://127.0.0.1:{port}/"
    try:
        server = Server(("127.0.0.1", port), Handler)
    except OSError:
        try:
            with urllib.request.urlopen(url + "api/version", timeout=2):
                pass
            print(f"Die Zentrale läuft schon: {url}")
            if open_browser:
                webbrowser.open(url)
            return
        except OSError:
            raise SystemExit(f"Port {port} ist von einem anderen Programm belegt. "
                             f"In config.json 'hub_port' ändern.")
    Handler.config = config
    Handler.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    print(f"Vinted Zentrale läuft: {url}  (Beenden: Fenster schließen oder Strg+C)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
