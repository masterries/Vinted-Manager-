"""Fill in the Vinted upload form (English UI on vinted.lu, as of October 2026).

Never submits - the user always does that. If Vinted changes the form,
"python -m vinted_hub explore" shows the new field names.
"""
from __future__ import annotations

from .core import debug_dir, load_config, prepare_upload_photos

SEL_PHOTOS = "[data-testid=add-photos-input], input[type=file]"
SEL_PHOTO_PREVIEW = "[data-testid^=image-wrapper-]"
SEL_TITLE = "[data-testid=title--input]"
SEL_DESCRIPTION = "[data-testid=description--input]"
SEL_PRICE = "[data-testid=price-input--input]"
SEL_BRAND_SEARCH = "#brand-search-input"
SEL_REJECT_COOKIES = "#onetrust-reject-all-handler"
# Dropdowns: "<name>-input" opens, "<name>-content" holds the options
DD_CATEGORY = "catalog-select-dropdown"
DD_BRAND = "brand-select-dropdown"
DD_SIZE = "category-size-single-grid"
DD_CONDITION = "category-condition-single-list"
DD_COLOR = "color-select-dropdown"
DD_MATERIAL = "category-material-multi-list"

# Values are stored as Vinted's English labels; old German values are still mapped (lowercase key -> label)
_CONDITION_LABELS = ["New with tags", "New without tags", "Very good", "Good", "Satisfactory"]
_LEGACY_CONDITIONS = {"neu mit etikett": "New with tags", "neu ohne etikett": "New without tags",
                      "sehr gut": "Very good", "gut": "Good", "zufriedenstellend": "Satisfactory"}
_COLOR_LABELS = ["Black", "Grey", "White", "Cream", "Beige", "Orange", "Red", "Burgundy", "Pink", "Purple",
                 "Blue", "Navy", "Turquoise", "Green", "Khaki", "Yellow", "Gold", "Silver", "Brown", "Multi"]
_LEGACY_COLORS = {"schwarz": "Black", "grau": "Grey", "weiß": "White", "weiss": "White", "creme": "Cream",
                  "rot": "Red", "bordeaux": "Burgundy", "rosa": "Pink", "lila": "Purple", "violett": "Purple",
                  "blau": "Blue", "türkis": "Turquoise", "grün": "Green", "gelb": "Yellow",
                  "silber": "Silver", "braun": "Brown", "cognac": "Brown", "mehrfarbig": "Multi"}
_MATERIAL_LABELS = ["Leather", "Suede", "Faux leather", "Canvas", "Rubber", "Jute"]
_LEGACY_MATERIALS = {"leder": "Leather", "wildleder": "Suede", "kunstleder": "Faux leather", "gummi": "Rubber"}

CONDITION_VALUES = {**{c.lower(): c for c in _CONDITION_LABELS}, **_LEGACY_CONDITIONS}
COLOR_VALUES = {**{c.lower(): c for c in _COLOR_LABELS}, **_LEGACY_COLORS}
MATERIAL_VALUES = {**{m.lower(): m for m in _MATERIAL_LABELS}, **_LEGACY_MATERIALS}


# After category/brand/condition/price Vinted shows a price recommendation (Bargain/Optimal/Premium)
PRICE_JS = r"""
() => {
  const t = document.body.innerText;
  const i = t.indexOf('Price recommendation');
  if (i < 0) return null;
  const part = t.slice(i, i + 400), out = {};
  const re = /€\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(Bargain|Optimal|Premium)/g;
  let m;
  while ((m = re.exec(part))) out[m[2].toLowerCase()] = parseFloat(m[1].replace(',', '.'));
  return Object.keys(out).length ? out : null;
}
"""


def read_price_recommendation(page) -> dict | None:
    from datetime import date
    for _ in range(12):
        try:
            rec = page.evaluate(PRICE_JS)
        except Exception:
            rec = None
        if rec:
            return {"bargain": rec.get("bargain"), "optimal": rec.get("optimal"),
                    "premium": rec.get("premium"), "date": date.today().isoformat()}
        page.wait_for_timeout(500)
    return None


OPTIONS = "[role=radio], [role=checkbox], [role=button]"


def _option(area, text: str, wait_ms: int = 5000):
    """Option whose first text line is exactly `text` (Vinted often shows an explanation below).
    Returns None if there is none."""
    candidates = area.locator(OPTIONS)
    js = """(els, t) => els.findIndex(e =>
        (e.innerText || '').trim().split('\\n')[0].trim().toLowerCase() === t.toLowerCase())"""
    for _ in range(max(1, wait_ms // 250)):
        idx = candidates.evaluate_all(js, text)
        if idx >= 0:
            return candidates.nth(idx)
        area.page.wait_for_timeout(250)
    return None


def _open(page, name: str):
    page.locator(f"[data-testid={name}-input]").first.click()
    content = page.locator(f"[data-testid={name}-content]").first
    content.wait_for(state="visible", timeout=6000)
    return content


def _close(page, name: str) -> None:
    """Close an open dropdown: Escape, otherwise click the page heading."""
    content = page.locator(f"[data-testid={name}-content]").first
    for attempt in (lambda: page.keyboard.press("Escape"), lambda: page.locator("h1").first.click()):
        if not content.is_visible():
            return
        try:
            attempt()
        except Exception:
            pass
        page.wait_for_timeout(400)


def _select(page, name: str, values: list[str]) -> list[str]:
    """Selects options in a dropdown. Returns the values that were not found."""
    content = _open(page, name)
    missing = []
    for value in values:
        opt = _option(content, value, wait_ms=2500)
        if opt is not None:
            opt.scroll_into_view_if_needed()
            opt.click()
            page.wait_for_timeout(500)
        else:
            missing.append(value)
    if missing:  # record the available options for debugging
        texts = content.locator(OPTIONS).all_inner_texts()
        target = debug_dir(load_config())
        target.mkdir(parents=True, exist_ok=True)
        (target / f"options_{name}.txt").write_text("\n".join(texts), encoding="utf-8")
    _close(page, name)
    return missing


def _known(value) -> bool:
    v = str(value or "").strip().lower()
    return bool(v) and v not in ("unknown", "unclear", "unbekannt", "unklar", "?", "[?]")


def fill_form(page, config: dict, listing: dict, details_only: bool = False) -> tuple[list[str], list[str]]:
    """Fills in the Vinted form (without saving). Returns (done, missing).
    details_only=True: only category, brand, size and condition (for the price recommendation)."""
    done, missing = [], []
    page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
    try:
        page.locator(SEL_TITLE).first.wait_for(state="visible", timeout=20000)
    except Exception:
        raise SystemExit("Upload-Formular nicht gefunden. Bist du im Vinted-Chrome eingeloggt? (Vinted Login.bat)")
    if page.locator(SEL_REJECT_COOKIES).is_visible():
        page.locator(SEL_REJECT_COOKIES).click()

    def text(sel, value, name):
        try:
            field = page.locator(sel).first
            field.fill(value)
            page.wait_for_timeout(300)
            done.append(name)
        except Exception:
            missing.append(name)

    if not details_only:
        # Photos: all at once, in the hub's order
        photos = prepare_upload_photos(config, listing)
        page.locator(SEL_PHOTOS).first.set_input_files([str(f) for f in photos])
        try:
            page.wait_for_function("([sel, n]) => document.querySelectorAll(sel).length >= n",
                                   arg=[SEL_PHOTO_PREVIEW, len(photos)], timeout=90000)
            done.append(f"{len(photos)} Fotos")
        except Exception:
            missing.append("Fotos prüfen (nicht alle Vorschauen erschienen)")
        text(SEL_TITLE, listing.get("title", ""), "Titel")
        text(SEL_DESCRIPTION, listing.get("description", ""), "Beschreibung")

    # Category: path like "Women > Shoes > Boots > Ankle boots"
    path = [t.strip() for t in str(listing.get("category", "")).split(">") if t.strip()]
    try:
        content = _open(page, DD_CATEGORY)
        for part in path:
            opt = _option(content, part)
            if opt is None:
                raise LookupError(part)
            opt.scroll_into_view_if_needed()
            opt.click()
            page.wait_for_timeout(800)
        page.locator(f"[data-testid={DD_BRAND}-input]").first.wait_for(state="visible", timeout=8000)
        done.append("Kategorie")
    except Exception:
        _close(page, DD_CATEGORY)
        missing.append(f"Kategorie ({listing.get('category')})")
        return done, missing + ["Marke", "Größe", "Zustand", "Farbe", "Preis"]

    # Brand via the search field
    brand = listing.get("brand", "")
    if str(brand).strip().lower() in ("ohne marke", "keine marke", "no brand"):
        missing.append("Marke (ohne Marke: bei Vinted leer lassen oder passend wählen)")
    elif _known(brand):
        try:
            content = _open(page, DD_BRAND)
            page.locator(SEL_BRAND_SEARCH).first.press_sequentially(brand, delay=60)
            page.wait_for_timeout(1500)
            hit = _option(content, brand, wait_ms=3000)
            if hit is not None:
                hit.click()
                page.wait_for_timeout(500)
                done.append("Marke")
            else:
                _close(page, DD_BRAND)
                missing.append(f"Marke ({brand} nicht in der Liste)")
        except Exception:
            missing.append(f"Marke ({brand})")
    else:
        missing.append("Marke (unbekannt)")

    size = str(listing.get("size", "")).strip()
    if _known(size):
        try:
            if _select(page, DD_SIZE, [size]):
                missing.append(f"Größe ({size} nicht gefunden)")
            else:
                done.append("Größe")
        except Exception:
            missing.append(f"Größe ({size})")
    else:
        missing.append("Größe (unbekannt)")

    condition = CONDITION_VALUES.get(str(listing.get("condition") or "").strip().lower())
    if condition:
        try:
            if _select(page, DD_CONDITION, [condition]):
                missing.append(f"Zustand ({condition})")
            else:
                done.append("Zustand")
        except Exception:
            missing.append(f"Zustand ({condition})")
    else:
        missing.append("Zustand")

    if details_only:
        return done, missing

    colors = [COLOR_VALUES.get(c.strip().lower()) for c in str(listing.get("color", "")).split(",") if c.strip()]
    colors = [c for c in dict.fromkeys(colors) if c][:2]
    if colors:
        try:
            not_found = _select(page, DD_COLOR, colors)
            if not_found:
                missing.append("Farbe (" + ", ".join(not_found) + ")")
            else:
                done.append("Farbe")
        except Exception:
            missing.append("Farbe")
    else:
        missing.append("Farbe")

    # Material only if not marked as uncertain (optional on Vinted)
    material = str(listing.get("material", "")).strip().lower()
    if (material and not material.startswith(("probably", "vermutlich"))
            and material in MATERIAL_VALUES):
        try:
            if not _select(page, DD_MATERIAL, [MATERIAL_VALUES[material]]):
                done.append("Material")
        except Exception:
            pass

    price = listing.get("price")
    text(SEL_PRICE, ("%g" % price) if price else "", "Preis")
    # Package size: Vinted preselects a suggestion itself
    return done, missing


def wait_for_submit(page) -> bool:
    """Waits until the user saved/uploaded (page leaves /items/new). False = tab closed."""
    try:
        page.wait_for_url(lambda url: "/items/new" not in url, timeout=0)
        return True
    except Exception:
        return False
