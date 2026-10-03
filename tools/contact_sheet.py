"""Finds new, not yet sorted photos in 0_input_photos and creates numbered contact sheets.

Usage:   python tools/contact_sheet.py
Result:  data/analysis/_contact_1.jpg, _contact_2.jpg, ... (16 photos each) and a list with capture times.
"Sorted" means: a file with the same name and size already exists in data/items/<folder>/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_hub import core  # noqa: E402


def sorted_photos(config: dict) -> set:
    root = core.items_dir(config)
    return {(f.name, f.stat().st_size) for f in root.glob("*/*") if f.is_file()}


def new_photos(config: dict) -> list[Path]:
    known = sorted_photos(config)
    inbox = core.input_dir(config)
    if not inbox.is_dir():
        return []
    return sorted(f for f in inbox.iterdir()
                  if f.is_file() and f.suffix.lower() in core.IMAGE_EXTENSIONS and (f.name, f.stat().st_size) not in known)


def capture_time(path: Path) -> str:
    from PIL import Image
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            return str(ex.get_ifd(0x8769).get(36867) or ex.get(306) or "")
    except Exception:
        return ""


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont
    config = core.load_config()
    out_dir = core.analysis_dir(config)
    photos = new_photos(config)
    if not photos:
        print("Keine neuen Fotos in 0_input_photos.")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("_contact_*.jpg"):
        old.unlink()
    for f in photos:
        print(f"{f.name:20} {capture_time(f)}")
    tile, columns, per_sheet = 360, 4, 16
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for start in range(0, len(photos), per_sheet):
        chunk = photos[start:start + per_sheet]
        rows = (len(chunk) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * tile, rows * tile), "white")
        draw = ImageDraw.Draw(sheet)
        for n, f in enumerate(chunk):
            im = core.open_image(f)
            im.thumbnail((tile - 8, tile - 8))
            x, y = (n % columns) * tile, (n // columns) * tile
            sheet.paste(im, (x + 4, y + 4))
            draw.rectangle([x + 4, y + 4, x + 4 + 12 + 18 * len(f.stem), y + 44], fill="black")
            draw.text((x + 10, y + 7), f.stem, fill="yellow", font=font)
        target = out_dir / f"_contact_{start // per_sheet + 1}.jpg"
        sheet.save(target, quality=85)
        print("Kontaktbogen:", target)
    print(f"{len(photos)} neue Fotos")


if __name__ == "__main__":
    main()
