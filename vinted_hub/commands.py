"""The hub's commands: login, explore, fill, fill-approved, prices, stats.

All commands work in the user's Vinted Chrome and never submit anything on Vinted.
"""
from __future__ import annotations

import json
import time

from .chrome import chrome_running, connect_chrome, is_logged_in, start_chrome
from .form import SEL_PRICE, fill_form, read_price_recommendation, wait_for_submit
from .core import debug_dir, read_listings, read_stats, update_fields, update_many, write_stats

# --- login ------------------------------------------------------------------

def cmd_login(config: dict) -> None:
    if chrome_running(config):
        print("Der Vinted-Chrome ist schon offen. Dort einfach einloggen.")
        return
    start_chrome(config, config["domain"])
    print("Chrome ist offen (eigenes Profil, getrennt von deinem normalen Chrome).")
    print("Bitte bei Vinted ganz normal selbst einloggen. Das Fenster darf offen bleiben.")


# --- explore (dump the form to build selectors) ------------------------------

FORM_JS = """
() => {
  const out = [];
  const sel = '[data-testid], input, textarea, select, button, [role="button"], [role="combobox"], [role="listbox"]';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    out.push({
      tag: el.tagName.toLowerCase(),
      testid: el.getAttribute('data-testid'),
      id: el.id || null,
      name: el.getAttribute('name'),
      type: el.getAttribute('type'),
      placeholder: el.getAttribute('placeholder'),
      aria: el.getAttribute('aria-label'),
      role: el.getAttribute('role'),
      text: (el.innerText || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 100),
      visible: r.width > 0 && r.height > 0,
    });
  }
  return out;
}
"""


def cmd_explore(config: dict) -> None:
    from playwright.sync_api import sync_playwright

    target = debug_dir(config)
    target.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser, ctx = connect_chrome(p, config)
        page = ctx.new_page()
        try:
            if not is_logged_in(page, config):
                page.screenshot(path=str(target / "not_logged_in.png"), full_page=True)
                raise SystemExit("Nicht eingeloggt (oder Upload-Formular nicht gefunden). Erst den Vinted-Chrome öffnen und einloggen (Vinted Login.bat)")
            page.wait_for_timeout(2000)
            elements = page.evaluate(FORM_JS)
            (target / "form.json").write_text(json.dumps(elements, ensure_ascii=False, indent=1), encoding="utf-8")
            (target / "form.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(target / "form.png"), full_page=True)
            print(f"{len(elements)} Elemente gespeichert in {target}")
        finally:
            page.close()


def _report(listing: dict, done: list[str], missing: list[str], rec: dict | None) -> None:
    print("  Ausgefüllt:", ", ".join(done) or "-")
    if missing:
        print("  Bitte von Hand ergänzen:", ", ".join(missing))
    if rec:
        print(f"  Vinted-Preisempfehlung: {rec['bargain']} / {rec['optimal']} / "
              f"{rec['premium']} € (günstig / optimal / premium), dein Preis: {listing.get('price')} €")
    if "[?" in listing.get("title", "") + listing.get("description", ""):
        print("  Achtung: Im Text stehen noch [?]-Platzhalter, vor dem Absenden ersetzen!")


def _fill_and_record(page, config: dict, listing: dict) -> None:
    done, missing = fill_form(page, config, listing)
    rec = read_price_recommendation(page) if "Kategorie" in done else None
    if rec:
        update_fields(config, listing["folder"], {"vinted_price": rec})
    _report(listing, done, missing, rec)


def cmd_fill(config: dict, folder: str) -> None:
    """Fill in a single listing (any status); the user submits it."""
    from playwright.sync_api import sync_playwright

    listing = next((i for i in read_listings(config) if i["folder"] == folder), None)
    if listing is None:
        raise SystemExit(f"Kein Inserat für Ordner {folder}")
    with sync_playwright() as p:
        browser, ctx = connect_chrome(p, config)
        page = ctx.new_page()
        page.bring_to_front()
        print(f"{listing['title']}")
        _fill_and_record(page, config, listing)
        debug_dir(config).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(debug_dir(config) / f"filled_{folder}.png"), full_page=True)
        print("  Jetzt im Chrome-Fenster prüfen und selbst auf 'Save draft' oder 'Upload' klicken.", flush=True)
        if wait_for_submit(page):
            update_fields(config, folder, {"status": "draft", "vinted_url": page.url})
            print("  ✓ Bei Vinted angelegt:", page.url)
        else:
            print("  Tab geschlossen, nichts gespeichert.")


# --- stats: views and favorites of the user's own listings (read only) ------

def _normalize(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _member_id(page, config: dict, listings: list[dict], stats: dict) -> str:
    import re
    if stats.get("member_id"):
        return str(stats["member_id"])
    for i in listings:
        m = re.search(r"/member/(\d+)", i.get("vinted_url") or "")
        if m:
            return m.group(1)
    page.goto(config["domain"], wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for href in page.eval_on_selector_all("a[href*='/member/']", "els => els.map(e => e.getAttribute('href'))"):
        m = re.search(r"/member/(\d+)", href or "")
        if m:
            return m.group(1)
    raise SystemExit("Eigene Vinted-Profil-ID nicht gefunden. Bist du im Vinted-Chrome eingeloggt?")


def _load_wardrobe(page, config: dict, member: str) -> list[dict]:
    """All own items via the same request the Vinted profile page makes."""
    page.goto(f"{config['domain']}/member/{member}", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    items, page_no = [], 1
    while True:
        response = page.evaluate("""async (url) => {
            const r = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
            return {status: r.status, text: await r.text()};
        }""", f"/api/v2/wardrobe/{member}/items?page={page_no}&per_page=96&order=relevance")
        if response["status"] != 200:
            raise SystemExit(f"Vinted hat die Abfrage abgelehnt (Status {response['status']}). Später nochmal versuchen.")
        data = json.loads(response["text"])
        items += data.get("items") or []
        if page_no >= ((data.get("pagination") or {}).get("total_pages") or 1):
            return items
        page_no += 1
        page.wait_for_timeout(1500)


def cmd_stats(config: dict) -> None:
    import difflib
    from datetime import datetime
    from playwright.sync_api import sync_playwright

    stats = read_stats(config)
    listings = read_listings(config)
    with sync_playwright() as p:
        browser, ctx = connect_chrome(p, config)
        page = ctx.new_page()
        try:
            member = _member_id(page, config, listings, stats)
            raw = _load_wardrobe(page, config, member)
        finally:
            page.close()

    now = datetime.now().isoformat(timespec="seconds")
    items = [{
        "id": a["id"], "title": a.get("title", ""), "url": a.get("url") or (config["domain"] + (a.get("path") or "")),
        "price": float((a.get("price") or {}).get("amount") or 0), "views": a.get("view_count") or 0,
        "favorites": a.get("favourite_count") or 0, "draft": bool(a.get("is_draft")), "sold": bool(a.get("is_closed")),
        "reserved": bool(a.get("is_reserved")), "hidden": bool(a.get("is_hidden")),
    } for a in raw]
    previous = {a["id"]: a for a in (stats["history"][-1]["items"] if stats.get("history") else [])}
    stats["member_id"] = member
    stats.setdefault("history", []).append({"time": now, "items": items})
    write_stats(config, stats)

    # Match Vinted items to hub listings: first by ID, then by title
    unmatched = [i for i in listings if not i.get("vinted_id")]
    changes, matched = {}, 0
    for a in items:
        listing = next((i for i in listings if i.get("vinted_id") == a["id"]), None)
        if listing is None:
            listing = next((i for i in unmatched if _normalize(i.get("title")) == _normalize(a["title"])), None)
        if listing is None and unmatched:
            best = max(unmatched, key=lambda i: difflib.SequenceMatcher(None, _normalize(i.get("title")), _normalize(a["title"])).ratio())
            if difflib.SequenceMatcher(None, _normalize(best.get("title")), _normalize(a["title"])).ratio() >= 0.8:
                listing = best
        if listing is None:
            continue
        if listing in unmatched:
            unmatched.remove(listing)
        matched += 1
        old = previous.get(a["id"], {})
        fields = {"vinted_id": a["id"], "vinted_url": a["url"],
                  "vinted_stats": {"views": a["views"], "favorites": a["favorites"], "time": now,
                                   "views_before": old.get("views"), "favorites_before": old.get("favorites"),
                                   "price": a["price"]}}
        status = listing.get("status")
        if a["sold"] and status in ("approved", "draft", "online"):
            fields["status"] = "sold"
        elif a["draft"] and status in ("approved", "online"):
            fields["status"] = "draft"
        elif not a["draft"] and not a["sold"] and status in ("approved", "draft"):
            fields["status"] = "online"
        changes[listing["folder"]] = fields
    update_many(config, changes)

    print(f"{len(items)} Artikel bei Vinted, {matched} davon Inseraten der Zentrale zugeordnet.")
    for a in sorted(items, key=lambda x: -x["views"]):
        old = previous.get(a["id"], {})
        plus = lambda new, k: f" (+{new - old[k]})" if k in old and new > old[k] else ""
        print(f"  {a['views']:4} Aufrufe{plus(a['views'], 'views'):7}  {a['favorites']:3} Fav.{plus(a['favorites'], 'favorites'):6}  {a['title'][:55]}")


def cmd_prices(config: dict, only: str | None) -> None:
    """Reads Vinted's price recommendation for listings not yet on Vinted.
    Only fills category, brand, size and condition and saves nothing on Vinted."""
    import random
    from playwright.sync_api import sync_playwright

    listings = [i for i in read_listings(config)
                if i.get("status") in ("new", "on_hold", "approved") and i.get("category")
                and (not only or i["folder"] == only)]
    if not listings:
        print("Keine passenden Inserate (brauchen eine Kategorie und dürfen noch nicht bei Vinted sein).")
        return
    with sync_playwright() as p:
        browser, ctx = connect_chrome(p, config)
        for n, listing in enumerate(listings, start=1):
            print(f"[{n}/{len(listings)}] {listing['title']}", flush=True)
            page = ctx.new_page()
            try:
                done, missing = fill_form(page, config, listing, details_only=True)
                rec = None
                if "Kategorie" in done:
                    rec = read_price_recommendation(page)
                    suggestion = listing.get("price") or listing.get("suggested_price")
                    if not rec and suggestion:  # sometimes only visible after entering a price
                        page.locator(SEL_PRICE).first.fill("%g" % suggestion)
                        rec = read_price_recommendation(page)
                if rec:
                    update_fields(config, listing["folder"], {"vinted_price": rec})
                    print(f"  Vinted: {rec['bargain']} / {rec['optimal']} / {rec['premium']} €"
                          + (f"  (ohne: {', '.join(missing)})" if missing else ""), flush=True)
                else:
                    print("  Keine Empfehlung gefunden" + (f" (fehlt: {', '.join(missing)})" if missing else ""), flush=True)
            except Exception as e:
                print(f"  Fehler: {e}", flush=True)
            finally:
                page.close(run_before_unload=False)  # discard the form, save nothing
            if n < len(listings):
                time.sleep(random.uniform(3, 7))
    print("Fertig.")


def cmd_fill_approved(config: dict, only: str | None) -> None:
    from playwright.sync_api import sync_playwright

    listings = [i for i in read_listings(config)
                if i.get("status") == "approved" and (not only or i["folder"] == only)]
    if not listings:
        print("Keine freigegebenen Inserate. Erst in der Zentrale freigeben.")
        return
    with sync_playwright() as p:
        browser, ctx = connect_chrome(p, config)
        page = ctx.new_page()
        page.bring_to_front()
        for n, listing in enumerate(listings, start=1):
            print(f"\n[{n}/{len(listings)}] {listing['title']}")
            _fill_and_record(page, config, listing)
            print("  Prüfen und selbst auf 'Save draft' oder 'Upload' klicken. Das Skript wartet so lange.", flush=True)
            if not wait_for_submit(page):
                print("Tab geschlossen, Upload beendet.")
                return
            update_fields(config, listing["folder"], {"status": "draft", "vinted_url": page.url})
            print("  ✓ Bei Vinted angelegt. Falls direkt veröffentlicht: in der Zentrale 'Ist online' klicken.")
        page.close()
    print("\nAlle freigegebenen Inserate sind bei Vinted angelegt.")
