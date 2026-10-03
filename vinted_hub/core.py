"""Vinted Hub basics: paths, configuration and data (listings, stats, photos).

All personal data lives under data/ (never in git):
  data/listings.json, data/stats.json, data/items/<folder>/, data/analysis/,
  data/archive/, data/debug/, data/browser-profile/
The user drops new photos into 0_input_photos/.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

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


def load_config() -> dict:
    with open(ROOT / "config.json", encoding="utf-8-sig") as f:
        return json.load(f)


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
        raise DataFileError(f"{path.name} ist fehlerhaft (Zeile {e.lineno}, Spalte {e.colno}): {e.msg}")
    except UnicodeDecodeError:
        raise DataFileError(f"{path.name} ist nicht als UTF-8 gespeichert")


def write_listings(config: dict, listings: list[dict]) -> None:
    """Safe write: unique temp file, flush to disk, keep one backup (.bak), then replace.
    Retry briefly if Windows is holding the file."""
    path = listings_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.stem + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(listings, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
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
    """Cross-process lock (hub + fill/stats scripts write the same file)."""

    def __init__(self, config: dict):
        self.path = listings_path(config).with_suffix(".lock")
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
        raise TimeoutError("listings.json ist gerade von einem anderen Programm gesperrt")

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
        raise FileNotFoundError(f"Foto-Ordner fehlt: {listing['folder']}")
    names = listing.get("photos", [])[: config["max_photos"]]
    missing = [n for n in names if not (base / n).is_file()]
    if not names or missing:
        raise FileNotFoundError("Foto fehlt: " + ", ".join(missing) if missing else "Keine Fotos ausgewählt")
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
