"""Imports checked analysis results (data/analysis/<folder>.json) into data/listings.json.

Usage:   python tools/import_listings.py [folder ...]     (none given: all data/analysis/*.json)
- Every file must pass the checker, otherwise it is skipped.
- New folders are appended. Existing listings are NOT overwritten,
  except with --replace and only while they are still "new" and no question has been answered.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_hub import core  # noqa: E402
from check_listing import check  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    replace = "--replace" in sys.argv
    config = core.load_config()
    out_dir = core.analysis_dir(config)
    files = [out_dir / f"{o}.json" for o in args] if args else sorted(out_dir.glob("[!_]*.json"))
    added, replaced, skipped, checked = [], [], [], []
    for path in files:
        listing = json.loads(path.read_text(encoding="utf-8-sig"))
        problems = check(listing)
        if problems:
            skipped.append(f"{path.name}: {problems[0]}")
            continue
        listing.setdefault("status", "new")
        listing.setdefault("history", [])
        checked.append(listing)
    # Read and write under the lock: the hub may run in parallel
    with core.file_lock(config):
        listings = core.read_listings(config)
        by_folder = {i["folder"]: n for n, i in enumerate(listings)}
        for listing in checked:
            o = listing["folder"]
            if o in by_folder:
                old = listings[by_folder[o]]
                untouched = old.get("status") == "new" and not any(q.get("answer") for q in old.get("questions") or [])
                if replace and untouched:
                    listings[by_folder[o]] = listing
                    replaced.append(o)
                else:
                    skipped.append(f"{o}: gibt es schon (mit --replace nur, solange unbearbeitet)")
                continue
            listings.append(listing)
            added.append(o)
        if added or replaced:
            core.write_listings(config, listings)
    print("Neu:", ", ".join(added) or "-")
    if replaced:
        print("Ersetzt:", ", ".join(replaced))
    for u in skipped:
        print("Übersprungen:", u)


if __name__ == "__main__":
    main()
