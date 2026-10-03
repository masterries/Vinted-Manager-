"""Fill in the Vinted upload form (English UI on vinted.lu, as of October 2026).

Never submits - the user always does that. If Vinted changes the form,
"python -m vinted_hub explore" shows the new field names.
"""
from __future__ import annotations

from .core import debug_dir, load_config, prepare_upload_photos
from .i18n import tr

SEL_PHOTOS = "[data-testid=add-photos-input], input[type=file]"
SEL_PHOTO_PREVIEW = "[data-testid^=image-wrapper-]"
SEL_TITLE = "[data-testid=title--input]"
SEL_DESCRIPTION = "[data-testid=description--input]"
SEL_PRICE = "[data-testid=price-input--input]"
SEL_BRAND_SEARCH = "#brand-search-input"
SEL_NO_BRAND = "#empty-brand"            # brand list: "No brand indicated" > "List without brand"
NO_BRAND_LABEL = "List without brand"
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


def select_no_brand(page) -> bool:
    """Brand dropdown: picks "No brand indicated" > "List without brand" (id "empty-brand"). True = clicked."""
    try:
        content = _open(page, DD_BRAND)
        hit = content.locator(SEL_NO_BRAND).first
        if not hit.count():
            hit = _option(content, NO_BRAND_LABEL, wait_ms=3000)
        if hit is None or not hit.count():
            _close(page, DD_BRAND)
            return False
        hit.scroll_into_view_if_needed()
        hit.click()
        page.wait_for_timeout(500)
        return True
    except Exception:
        _close(page, DD_BRAND)
        return False


def _known(value) -> bool:
    v = str(value or "").strip().lower()
    return bool(v) and v not in ("unknown", "unclear", "unbekannt", "unklar", "?", "[?]")


def fill_form(page, config: dict, listing: dict, details_only: bool = False) -> tuple[list[str], list[str], bool]:
    """Fills in the Vinted form (without saving). Returns (done, missing, category_ok):
    done/missing are field names for the log (UI language), category_ok tells whether the
    category was selected (Vinted then shows its price recommendation).
    details_only=True: only category, brand, size and condition (for the price recommendation)."""
    done, missing = [], []
    page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
    try:
        page.locator(SEL_TITLE).first.wait_for(state="visible", timeout=20000)
    except Exception:
        raise SystemExit(tr("Upload form not found. Are you logged in to the Vinted Chrome? (Vinted Login.bat)"))
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
            done.append(tr("{count} photos", count=len(photos)))
        except Exception:
            missing.append(tr("Check photos (not all previews appeared)"))
        text(SEL_TITLE, listing.get("title", ""), tr("Title"))
        text(SEL_DESCRIPTION, listing.get("description", ""), tr("Description"))

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
        done.append(tr("Category"))
    except Exception:
        _close(page, DD_CATEGORY)
        missing.append(tr("Category ({category})", category=listing.get("category")))
        return done, missing + [tr("Brand"), tr("Size"), tr("Condition"), tr("Colour"), tr("Price")], False

    # Brand via the search field
    brand = listing.get("brand", "")
    if str(brand).strip().lower() in ("ohne marke", "keine marke", "no brand"):
        if select_no_brand(page):
            done.append(tr("Brand ({brand})", brand=NO_BRAND_LABEL))
        else:
            missing.append(tr("Brand (choose '{label}' on Vinted)", label=NO_BRAND_LABEL))
    elif _known(brand):
        try:
            content = _open(page, DD_BRAND)
            page.locator(SEL_BRAND_SEARCH).first.press_sequentially(brand, delay=60)
            page.wait_for_timeout(1500)
            hit = _option(content, brand, wait_ms=3000)
            if hit is not None:
                hit.click()
                page.wait_for_timeout(500)
                done.append(tr("Brand"))
            else:
                _close(page, DD_BRAND)
                missing.append(tr("Brand ({brand} not in the list)", brand=brand))
        except Exception:
            _close(page, DD_BRAND)
            missing.append(tr("Brand ({brand})", brand=brand))
    else:
        missing.append(tr("Brand (unknown)"))

    size = str(listing.get("size", "")).strip()
    if _known(size):
        try:
            if _select(page, DD_SIZE, [size]):
                missing.append(tr("Size ({size} not found)", size=size))
            else:
                done.append(tr("Size"))
        except Exception:
            missing.append(tr("Size ({size})", size=size))
    else:
        missing.append(tr("Size (unknown)"))

    condition = CONDITION_VALUES.get(str(listing.get("condition") or "").strip().lower())
    if condition:
        try:
            if _select(page, DD_CONDITION, [condition]):
                missing.append(tr("Condition ({condition})", condition=condition))
            else:
                done.append(tr("Condition"))
        except Exception:
            missing.append(tr("Condition ({condition})", condition=condition))
    else:
        missing.append(tr("Condition"))

    if details_only:
        return done, missing, True

    colors = [COLOR_VALUES.get(c.strip().lower()) for c in str(listing.get("color", "")).split(",") if c.strip()]
    colors = [c for c in dict.fromkeys(colors) if c][:2]
    if colors:
        try:
            not_found = _select(page, DD_COLOR, colors)
            if not_found:
                missing.append(tr("Colour ({colors})", colors=", ".join(not_found)))
            else:
                done.append(tr("Colour"))
        except Exception:
            missing.append(tr("Colour"))
    else:
        missing.append(tr("Colour"))

    # Material only if not marked as uncertain (optional on Vinted)
    material = str(listing.get("material", "")).strip().lower()
    if (material and not material.startswith(("probably", "vermutlich"))
            and material in MATERIAL_VALUES):
        try:
            if not _select(page, DD_MATERIAL, [MATERIAL_VALUES[material]]):
                done.append(tr("Material"))
        except Exception:
            pass

    price = listing.get("price")
    text(SEL_PRICE, ("%g" % price) if price else "", tr("Price"))

    # Parcel size: Vinted preselects its own suggestion (often "Large" for shoes) - choose ours
    package = PACKAGE_SIZES.get(str(listing.get("package") or "").strip().lower(), "Medium")
    if select_package(page, package):
        done.append(tr("Package size ({size})", size=package))
    else:
        _dump_shipping(page, config, listing)
        missing.append(tr("Package size ({size})", size=package))
    return done, missing, True


# --- parcel size ("Shipping" > "Select your parcel size": cells Small / Medium / Large / Large and heavy) ---
# Our value -> Vinted's cell title. "Large and heavy" is never chosen.
PACKAGE_SIZES = {"small": "Small", "medium": "Medium", "large": "Large",
                 "klein": "Small", "mittel": "Medium", "groß": "Large", "gross": "Large"}
SEL_RADIO = "input[type=radio], [role=radio]"

# Finds the radio whose cell (largest ancestor holding only this one radio) has `name` as its first text line
# ("Recommended" badges are skipped). Marks the cell with data-vh-package so Playwright can click it.
PACKAGE_JS = r"""
(name) => {
  const radios = [...document.querySelectorAll('input[type=radio], [role=radio]')];
  const count = (el) => el.querySelectorAll('input[type=radio], [role=radio]').length;
  const title = (el) => (el.innerText || '').split('\n').map(s => s.trim())
      .filter(s => s && s.toLowerCase() !== 'recommended')[0] || '';
  for (const r of radios) {
    let cell = r;
    while (cell.parentElement && cell.parentElement !== document.body && count(cell.parentElement) === 1) {
      cell = cell.parentElement;
    }
    if (title(cell).toLowerCase() !== name.toLowerCase()) continue;
    document.querySelectorAll('[data-vh-package],[data-vh-package-radio]').forEach(el => {
      el.removeAttribute('data-vh-package'); el.removeAttribute('data-vh-package-radio'); });
    cell.setAttribute('data-vh-package', name);
    r.setAttribute('data-vh-package-radio', name);
    r.scrollIntoView({block: 'center'});
    return {found: true, checked: r.checked === true || r.getAttribute('aria-checked') === 'true'};
  }
  return {found: false};
}
"""


def select_package(page, name: str, timeout_ms: int = 8000) -> bool:
    """Selects the parcel size cell `name` (Small / Medium / Large). True = selected (verified).
    Never raises - False only means "choose it by hand"."""
    def state() -> dict:
        return page.evaluate(PACKAGE_JS, name)  # finds and marks the cell anew: a re-render cannot fool the check
    try:
        page.wait_for_function(f"() => ({PACKAGE_JS})({name!r}).found", timeout=timeout_ms, polling=250)
        if state().get("checked"):
            return True
        attempts = (
            lambda: page.locator(f'[data-vh-package="{name}"]').first.click(timeout=3000),
            # click event on the radio itself; a force click would hit whatever lies on top of it
            lambda: page.locator(f'[data-vh-package-radio="{name}"]').first.dispatch_event("click", timeout=3000),
        )
        for attempt in attempts:
            try:
                attempt()
                page.wait_for_timeout(500)
            except Exception:
                pass
            now = state()
            if now.get("checked"):
                return True
            if not now.get("found"):  # page changed, e.g. the user already submitted
                return False
        return False
    except Exception:
        return False


def _dump_shipping(page, config: dict, listing: dict) -> None:
    """Saves the shipping section's HTML so the parcel size selectors can be fixed (data/debug/)."""
    try:
        html = page.evaluate("""() => {
            const all = [...document.querySelectorAll('h1,h2,h3,h4,div,span,p')];
            const head = all.find(el => /parcel size|shipping/i.test(el.innerText || '') && (el.innerText || '').length < 60);
            let el = head;
            for (let i = 0; el && i < 6 && el.querySelectorAll('input[type=radio], [role=radio]').length < 3; i++) el = el.parentElement;
            return (el || document.body).outerHTML;
        }""")
        target = debug_dir(config)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"shipping_{listing['folder']}.html").write_text(html, encoding="utf-8")
    except Exception:
        pass


def wait_for_submit(page) -> bool:
    """Waits until the user saved/uploaded (page leaves /items/new). False = tab closed."""
    try:
        page.wait_for_url(lambda url: "/items/new" not in url, timeout=0)
        return True
    except Exception:
        return False
