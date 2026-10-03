"""Vinted Hub commands:  python -m vinted_hub <command>

  serve          start the local web hub (http://127.0.0.1:8765), alias: hub
  login          open the Vinted Chrome (log in manually once)
  fill           fill one listing into the Vinted form (the user submits)
  fill-approved  fill all approved listings one after another
  prices         read Vinted's price recommendation (saves nothing on Vinted)
  stats          fetch and store views and favourites of all own listings
  explore        dump the upload form (when Vinted changes the form)
  settings       show the settings as JSON; "settings set key=value ..." changes them
"""
from __future__ import annotations

import argparse
import json

from . import commands
from .core import SETTINGS_CHOICES, current_settings, load_config, save_settings
from .i18n import tr


def cmd_settings(config: dict, action: str | None, pairs: list[str]) -> None:
    """Without arguments: print the effective settings as one line of JSON.
    "set key=value ...": validate, save in data/settings.json and print the new settings."""
    if action is None:
        if pairs:
            raise SystemExit(tr("Use: settings set key=value ..."))
        print(json.dumps(current_settings(config)))
        return
    if not pairs:
        raise SystemExit(tr("Use: settings set key=value ... (keys: {keys})", keys=", ".join(SETTINGS_CHOICES)))
    changes = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(tr("Expected key=value, got: {text}", text=pair))
        changes[key.strip()] = value.strip()
    try:
        print(json.dumps(save_settings(config, changes)))
    except (ValueError, OSError) as e:  # OSError incl. TimeoutError: settings.json locked (message already translated)
        raise SystemExit(str(e))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m vinted_hub", description="Vinted Hub")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve", aliases=["hub"], help="start the local web hub")
    s.add_argument("--no-browser", action="store_true", help="do not open the page automatically")
    sub.add_parser("login", help="open the Vinted Chrome and log in manually")
    sub.add_parser("explore", help="dump the upload form (for development)")
    f = sub.add_parser("fill", help="fill one listing into the Vinted form (you submit it)")
    f.add_argument("folder", help="folder name, e.g. 01_sandaletten_plateau_creme")
    fa = sub.add_parser("fill-approved", help="fill approved listings one after another")
    fa.add_argument("--only", help="only this folder")
    pr = sub.add_parser("prices", help="read Vinted's price recommendation (saves nothing on Vinted)")
    pr.add_argument("--only", help="only this folder")
    sub.add_parser("stats", help="fetch and store views and favourites of own listings")
    st = sub.add_parser("settings", help="show the settings as JSON, or change them with: settings set key=value ...",
                        description="Settings: " + "; ".join(f"{k} = {' | '.join(v)}" for k, v in SETTINGS_CHOICES.items()))
    st.add_argument("action", nargs="?", choices=["set"], help="set: change settings")
    st.add_argument("pairs", nargs="*", metavar="key=value", help="e.g. description_language=de")
    args = parser.parse_args()

    config = load_config()
    if args.command in ("serve", "hub"):
        from . import server
        server.run(config, not args.no_browser)
    elif args.command == "login":
        commands.cmd_login(config)
    elif args.command == "explore":
        commands.cmd_explore(config)
    elif args.command == "fill":
        commands.cmd_fill(config, args.folder)
    elif args.command == "fill-approved":
        commands.cmd_fill_approved(config, args.only)
    elif args.command == "prices":
        commands.cmd_prices(config, args.only)
    elif args.command == "stats":
        commands.cmd_stats(config)
    elif args.command == "settings":
        cmd_settings(config, args.action, args.pairs)


if __name__ == "__main__":
    main()
