"""Findet neue, noch nicht einsortierte Fotos in 0_input_foto und erstellt nummerierte Kontaktbögen.

Aufruf:  python werkzeuge/kontaktbogen.py
Ergebnis: analyse/_kontakt_1.jpg, _kontakt_2.jpg, ... (je 16 Fotos) und eine Liste mit Aufnahmezeit.
"Einsortiert" heißt: eine Datei mit gleichem Namen und gleicher Größe liegt schon in schuhe/<ordner>/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vinted  # noqa: E402

EINGANG = vinted.BASIS / "0_input_foto"
AUS = vinted.BASIS / "analyse"


def einsortiert(config: dict) -> set:
    wurzel = vinted.artikel_wurzel(config)
    return {(f.name, f.stat().st_size) for f in wurzel.glob("*/*") if f.is_file()}


def neue_fotos(config: dict) -> list[Path]:
    bekannt = einsortiert(config)
    return sorted(f for f in EINGANG.iterdir()
                  if f.is_file() and f.suffix.lower() in vinted.BILD_ENDUNGEN and (f.name, f.stat().st_size) not in bekannt)


def aufnahmezeit(pfad: Path) -> str:
    from PIL import Image
    try:
        with Image.open(pfad) as im:
            ex = im.getexif()
            return str(ex.get_ifd(0x8769).get(36867) or ex.get(306) or "")
    except Exception:
        return ""


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont
    config = vinted.lade_config()
    fotos = neue_fotos(config)
    if not fotos:
        print("Keine neuen Fotos in 0_input_foto.")
        return
    AUS.mkdir(exist_ok=True)
    for alt in AUS.glob("_kontakt_*.jpg"):
        alt.unlink()
    for f in fotos:
        print(f"{f.name:20} {aufnahmezeit(f)}")
    kachel, spalten, pro_bogen = 360, 4, 16
    try:
        schrift = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        schrift = ImageFont.load_default()
    for start in range(0, len(fotos), pro_bogen):
        teil = fotos[start:start + pro_bogen]
        zeilen = (len(teil) + spalten - 1) // spalten
        bogen = Image.new("RGB", (spalten * kachel, zeilen * kachel), "white")
        zeichnen = ImageDraw.Draw(bogen)
        for n, f in enumerate(teil):
            im = vinted.oeffne_bild(f)
            im.thumbnail((kachel - 8, kachel - 8))
            x, y = (n % spalten) * kachel, (n // spalten) * kachel
            bogen.paste(im, (x + 4, y + 4))
            zeichnen.rectangle([x + 4, y + 4, x + 4 + 12 + 18 * len(f.stem), y + 44], fill="black")
            zeichnen.text((x + 10, y + 7), f.stem, fill="yellow", font=schrift)
        ziel = AUS / f"_kontakt_{start // pro_bogen + 1}.jpg"
        bogen.save(ziel, quality=85)
        print("Kontaktbogen:", ziel)
    print(f"{len(fotos)} neue Fotos")


if __name__ == "__main__":
    main()
