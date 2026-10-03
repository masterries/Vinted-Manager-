"""Vinted Hub basics: paths, configuration, settings and data (listings, stats, photos).

All personal data lives under data/ (never in git):
  data/listings.json, data/settings.json, data/stats.json, data/items/<folder>/,
  data/analysis/, data/archive/, data/debug/, data/browser-profile/
The user drops new photos into 0_input_photos/.
config.json (in git) holds the defaults, data/settings.json the user's own choices.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from .i18n import tr

ROOT = Path(__file__).resolve().parent.parent  # project folder
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
try:  # read iPhone photos (HEIC)
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    IMAGE_EXTENSIONS -= {".heic", ".heif"}

STATUSES = ["new", "approved", "draft", "online", "sold", "on_hold"]
CONDITIONS = ["New with tags", "New without tags", "Very good", "Good", "Satisfactory"]
PACKAGES = ["Small", "Medium", "Large"]
TEXT_FIELDS = ["title", "description", "category", "brand", "size", "condition",
               "color", "material", "heel_height", "shape", "package", "notes"]
NUMBER_FIELDS = ["price", "min_price"]


# Settings the user can change in the hub (or: python -m vinted_hub settings set key=value)
#   ui_language          hub, job logs, messages and the seller-facing texts of new analyses
#   title_language       listing titles written by new analyses
#   description_language listing descriptions written by new analyses (one language, never both)
SETTINGS_CHOICES = {"ui_language": ["en", "de"], "title_language": ["en", "de"], "description_language": ["en", "de"]}
SETTINGS_DEFAULTS = {"ui_language": "en", "title_language": "en", "description_language": "en"}
_settings_lock = threading.Lock()  # two hub requests saving at the same time (other processes: file_lock)


def _read_config_file() -> dict:
    with open(ROOT / "config.json", encoding="utf-8-sig") as f:
        return json.load(f)


def _valid_settings(data) -> dict:
    """Only known keys with allowed values; everything else is ignored."""
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items()
            if k in SETTINGS_CHOICES and isinstance(v, str) and v in SETTINGS_CHOICES[k]}


def load_config() -> dict:
    """config.json merged with the valid entries of data/settings.json."""
    config = _read_config_file()
    for key, value in SETTINGS_DEFAULTS.items():
        if config.get(key) not in SETTINGS_CHOICES[key]:
            config[key] = value
    config.update(saved_settings(config))
    return config


# --- Folders and files --------------------------------------------------------

def data_dir(config: dict) -> Path:
    return ROOT / config.get("data_folder", "data")


def input_dir(config: dict) -> Path:
    """Where the user drops new, unsorted photos."""
    return ROOT / config.get("input_folder", "0_input_photos")


def items_dir(config: dict) -> Path:
    """One subfolder per pair with its photos (data/items/<NN_name>/)."""
    return data_dir(config) / "items"


def listings_path(config: dict) -> Path:
    return data_dir(config) / "listings.json"


def stats_path(config: dict) -> Path:
    return data_dir(config) / "stats.json"


def settings_path(config: dict) -> Path:
    """The user's own settings (personal, not in git)."""
    return data_dir(config) / "settings.json"


def profile_dir(config: dict) -> Path:
    """Chrome profile holding the Vinted login."""
    return data_dir(config) / "browser-profile"


def analysis_dir(config: dict) -> Path:
    return data_dir(config) / "analysis"


def debug_dir(config: dict) -> Path:
    """Debug output (form dumps, screenshots) - contains account data."""
    return data_dir(config) / "debug"


def archive_dir(config: dict) -> Path:
    return data_dir(config) / "archive"


# --- listings.json ------------------------------------------------------------

class DataFileError(Exception):
    """listings.json cannot be read (e.g. broken by a manual edit)."""



def read_listings(config: dict) -> list[dict]:
    path = listings_path(config)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise DataFileError(tr("{name} is broken (line {line}, column {column}): {error}",
                               name=path.name, line=e.lineno, column=e.colno, error=e.msg))
    except UnicodeDecodeError:
        raise DataFileError(tr("{name} is not saved as UTF-8", name=path.name))


def write_listings(config: dict, listings: list[dict]) -> None:
    write_file_safely(listings_path(config), json.dumps(listings, ensure_ascii=False, indent=2), backup=True)


def write_file_safely(path: Path, text: str, backup: bool = False) -> None:
    """Safe write: unique temp file, flush to disk, optionally keep one backup (.bak), then replace.
    Retry briefly if Windows is holding the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.stem + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if backup and path.exists():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        for attempt in range(10):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class file_lock:
    """Cross-process lock for a data file: by default listings.json (hub + fill/stats scripts write it),
    or the file given as `path`, e.g. settings_path(config) (hub + CLI "settings set").
    The lock file sits next to it: data/listings.lock, data/settings.lock."""

    def __init__(self, config: dict, path: Path | None = None):
        target = Path(path) if path is not None else listings_path(config)
        self.name = target.name  # named in the timeout message
        self.path = target.with_suffix(".lock")
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "a+")
        for _ in range(200):  # wait up to about 10 seconds
            try:
                if os.name == "nt":
                    import msvcrt
                    self.file.seek(0)
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                time.sleep(0.05)
        self.file.close()
        raise TimeoutError(tr("{name} is locked by another program right now", name=self.name))

    def __exit__(self, *args):
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()


def update_many(config: dict, changes: dict) -> None:
    """Update fields of several listings in one step: {folder: {field: value}}."""
    from datetime import datetime
    if not changes:
        return
    with file_lock(config):
        listings = read_listings(config)
        for listing in listings:
            if listing["folder"] in changes:
                listing.update(changes[listing["folder"]])
                listing["updated_at"] = datetime.now().isoformat(timespec="seconds")
        write_listings(config, listings)


def update_fields(config: dict, folder: str, fields: dict) -> None:
    """Change single fields of one listing, leave everything else untouched."""
    update_many(config, {folder: fields})


def photos_in_folder(config: dict, folder: str) -> list[str]:
    """File names of all original photos of an item (without _upload/_preview)."""
    d = items_dir(config) / folder
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS)


def empty_listing(config: dict, folder: str) -> dict:
    listing = {"folder": folder, "status": "new", "photos": photos_in_folder(config, folder), "hints": []}
    for field in TEXT_FIELDS:
        listing[field] = ""
    for field in NUMBER_FIELDS:
        listing[field] = None
    settings = current_settings(config)
    listing["title_language"] = settings["title_language"]
    listing["description_language"] = settings["description_language"]
    return listing


def open_image(path: Path):
    from PIL import Image, ImageOps
    im = Image.open(path)
    return ImageOps.exif_transpose(im).convert("RGB")


def prepare_upload_photos(config: dict, listing: dict) -> list[Path]:
    """Write the chosen photos as _upload/01.jpg, 02.jpg, ... in the chosen order:
    rotated, downscaled and without metadata (GPS)."""
    base = items_dir(config) / listing["folder"]
    if not base.is_dir():
        raise FileNotFoundError(tr("Photo folder missing: {folder}", folder=listing["folder"]))
    names = listing.get("photos", [])[: config["max_photos"]]
    missing = [n for n in names if not (base / n).is_file()]
    if missing:
        raise FileNotFoundError(tr("Photo missing: {files}", files=", ".join(missing)))
    if not names:
        raise FileNotFoundError(tr("No photos selected"))
    out = base / "_upload"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    paths = []
    for i, name in enumerate(names, start=1):
        im = open_image(base / name)
        im.thumbnail((2000, 2000))
        target = out / f"{i:02d}.jpg"
        # saved without exif= -> no GPS/camera metadata in the upload
        im.save(target, "JPEG", quality=90)
        paths.append(target)
    return paths


# --- stats.json ---------------------------------------------------------------

def read_stats(config: dict) -> dict:
    path = stats_path(config)
    if not path.exists():
        return {"member_id": None, "history": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_stats(config: dict, data: dict) -> None:
    path = stats_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.stem + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1))
    os.replace(tmp, path)


# --- settings.json --------------------------------------------------------------

def saved_settings(config: dict) -> dict:
    """The valid entries of data/settings.json (missing or broken file: {})."""
    try:
        data = json.loads(settings_path(config).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return _valid_settings(data)


def current_settings(config: dict) -> dict:
    """The effective settings right now: config.json defaults, overridden by data/settings.json.
    Both files are read fresh, so a change made in another tab or process counts at once."""
    try:
        defaults = _read_config_file()
    except (OSError, ValueError):
        defaults = config
    settings = {k: defaults[k] if defaults.get(k) in SETTINGS_CHOICES[k] else v
                for k, v in SETTINGS_DEFAULTS.items()}
    settings.update(saved_settings(config))
    return settings


def check_settings(changes) -> dict:
    """Validates {key: value}; raises ValueError with a message for the user."""
    if not isinstance(changes, dict):
        raise ValueError(tr("Invalid settings"))
    for key, value in changes.items():
        if key not in SETTINGS_CHOICES:
            raise ValueError(tr("Unknown setting: {key}", key=key))
        if not isinstance(value, str) or value not in SETTINGS_CHOICES[key]:
            raise ValueError(tr("Invalid value for {key}: {value} (allowed: {allowed})",
                                key=key, value=value, allowed=", ".join(SETTINGS_CHOICES[key])))
    return dict(changes)


def save_settings(config: dict, changes: dict) -> dict:
    """Validates and saves changed settings in data/settings.json (atomic write, keeps the
    user's other choices). Returns the new effective settings and updates `config` with them."""
    changes = check_settings(changes)
    if changes:
        # read-change-write under a lock shared with other processes (hub + CLI at the same moment)
        with _settings_lock, file_lock(config, settings_path(config)):
            saved = saved_settings(config)
            saved.update(changes)
            ordered = {k: saved[k] for k in SETTINGS_CHOICES if k in saved}
            write_file_safely(settings_path(config), json.dumps(ordered, ensure_ascii=False, indent=2) + "\n")
        from . import i18n
        i18n.forget_language()  # the next message already uses the new language
    settings = current_settings(config)
    config.update(settings)
    return settings
