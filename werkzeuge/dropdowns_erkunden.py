"""Einmaliges Erkunden der Auswahllisten im Vinted-Formular (speichert nichts bei Vinted).

Klickt Kategorie Women > Shoes > ... durch und speichert nach jedem Schritt,
welche Elemente sichtbar sind. Am Ende wird der Tab ohne Speichern geschlossen.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vinted  # noqa: E402

ZIEL = Path(__file__).resolve().parent.parent / "erkunden" / "dropdowns"
ZIEL.mkdir(parents=True, exist_ok=True)

SICHTBAR_JS = """
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


def speichere(page, name):
    daten = page.evaluate(SICHTBAR_JS)
    (ZIEL / f"{name}.json").write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    page.screenshot(path=str(ZIEL / f"{name}.png"), full_page=True)
    print(f"{name}: {len(daten)} Elemente")


def klicke_text(page, text):
    """Klickt das sichtbare Element mit genau diesem Text innerhalb der offenen Auswahlliste."""
    kandidaten = page.locator("[data-testid*=catalog-select-dropdown-content], [data-testid*=dropdown-content]")
    bereich = kandidaten.first if kandidaten.count() else page
    ziel = bereich.get_by_text(text, exact=True).first
    ziel.scroll_into_view_if_needed()
    ziel.click()
    page.wait_for_timeout(1200)


def main():
    from playwright.sync_api import sync_playwright

    config = vinted.lade_config()
    with sync_playwright() as p:
        browser, ctx = vinted.verbinde_chrome(p, config)
        page = ctx.new_page()
        try:
            page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
            page.locator("[data-testid=catalog-select-dropdown-input]").wait_for(timeout=20000)
            page.wait_for_timeout(1500)

            page.locator("[data-testid=catalog-select-dropdown-input]").click()
            page.wait_for_timeout(1500)
            speichere(page, "01_kategorie_offen")

            for i, schritt in enumerate(["Women", "Shoes", "Boots"], start=2):
                try:
                    klicke_text(page, schritt)
                    speichere(page, f"{i:02d}_nach_{schritt}")
                except Exception as e:
                    print(f"Schritt {schritt} fehlgeschlagen: {e}")
                    speichere(page, f"{i:02d}_fehler_{schritt}")
                    break

            # Blatt-Kategorie: erste Unterkategorie mit "Chelsea" oder "Ankle" wählen
            for text in ["Chelsea boots", "Chelsea & slip-on boots", "Ankle boots"]:
                if page.get_by_text(text, exact=True).count():
                    klicke_text(page, text)
                    break
            page.wait_for_timeout(2000)
            speichere(page, "05_nach_blattkategorie")

            # Detailfelder nacheinander öffnen und Optionen ansehen
            for testid in ["brand-select-dropdown-input", "size-select-dropdown-input",
                           "condition-select-dropdown-input", "status-select-dropdown-input",
                           "color-select-dropdown-input", "material-select-dropdown-input"]:
                feld = page.locator(f"[data-testid={testid}]")
                if not feld.count():
                    continue
                try:
                    feld.first.click()
                    page.wait_for_timeout(1500)
                    speichere(page, f"10_offen_{testid}")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(600)
                except Exception as e:
                    print(f"{testid}: {e}")
        finally:
            page.wait_for_timeout(500)
            page.close()  # ohne Speichern
            print("Tab geschlossen, nichts gespeichert.")


if __name__ == "__main__":
    main()
