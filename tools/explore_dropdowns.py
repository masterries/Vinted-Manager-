"""One-off exploration of the dropdowns in the Vinted listing form (saves nothing on Vinted).

Clicks through category Women > Shoes > ... and records after each step
which elements are visible. At the end the tab is closed without saving.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_hub import chrome, core  # noqa: E402


VISIBLE_JS = """
() => {
  const out = [];
  const sel = '[data-testid], [role=option], [role=radio], [role=checkbox], [role=listbox], [role=button], li, input';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (el.closest('header, footer, #onetrust-consent-sdk')) continue;
    out.push({
      tag: el.tagName.toLowerCase(), testid: el.getAttribute('data-testid'), id: el.id || null,
      role: el.getAttribute('role'), type: el.getAttribute('type'), name: el.getAttribute('name'),
      placeholder: el.getAttribute('placeholder'), checked: el.checked === undefined ? null : el.checked,
      text: (el.innerText || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 80),
    });
  }
  return out;
}
"""


def save(page, name):
    target = core.debug_dir(core.load_config()) / "dropdowns"
    target.mkdir(parents=True, exist_ok=True)
    data = page.evaluate(VISIBLE_JS)
    (target / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    page.screenshot(path=str(target / f"{name}.png"), full_page=True)
    print(f"{name}: {len(data)} Elemente")


def click_text(page, text):
    """Clicks the visible element with exactly this text inside the open dropdown."""
    candidates = page.locator("[data-testid*=catalog-select-dropdown-content], [data-testid*=dropdown-content]")
    scope = candidates.first if candidates.count() else page
    target = scope.get_by_text(text, exact=True).first
    target.scroll_into_view_if_needed()
    target.click()
    page.wait_for_timeout(1200)


def main():
    from playwright.sync_api import sync_playwright

    config = core.load_config()
    with sync_playwright() as p:
        browser, ctx = chrome.connect_chrome(p, config)
        page = ctx.new_page()
        try:
            page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
            page.locator("[data-testid=catalog-select-dropdown-input]").wait_for(timeout=20000)
            page.wait_for_timeout(1500)

            page.locator("[data-testid=catalog-select-dropdown-input]").click()
            page.wait_for_timeout(1500)
            save(page, "01_category_open")

            for i, step in enumerate(["Women", "Shoes", "Boots"], start=2):
                try:
                    click_text(page, step)
                    save(page, f"{i:02d}_after_{step}")
                except Exception as e:
                    print(f"Schritt {step} fehlgeschlagen: {e}")
                    save(page, f"{i:02d}_error_{step}")
                    break

            # Leaf category: pick the first subcategory with "Chelsea" or "Ankle"
            for text in ["Chelsea boots", "Chelsea & slip-on boots", "Ankle boots"]:
                if page.get_by_text(text, exact=True).count():
                    click_text(page, text)
                    break
            page.wait_for_timeout(2000)
            save(page, "05_after_leaf_category")

            # Open the detail fields one by one and look at the options
            for testid in ["brand-select-dropdown-input", "size-select-dropdown-input",
                           "condition-select-dropdown-input", "status-select-dropdown-input",
                           "color-select-dropdown-input", "material-select-dropdown-input"]:
                field = page.locator(f"[data-testid={testid}]")
                if not field.count():
                    continue
                try:
                    field.first.click()
                    page.wait_for_timeout(1500)
                    save(page, f"10_open_{testid}")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(600)
                except Exception as e:
                    print(f"{testid}: {e}")
        finally:
            page.wait_for_timeout(500)
            page.close()  # without saving
            print("Tab geschlossen, nichts gespeichert.")


if __name__ == "__main__":
    main()
