"""Vinted Chrome: a plain Chrome with its own profile (data/browser-profile).

It is NOT launched by Playwright (that triggered Vinted's bot detection). The user logs in
manually; the commands then connect via the local debug port (CDP).
"""
from __future__ import annotations

import os
from pathlib import Path

from .core import profile_dir
from .i18n import tr

def chrome_path() -> str:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    raise SystemExit(tr("Google Chrome not found."))


def cdp_url(config: dict) -> str:
    return f"http://127.0.0.1:{config.get('chrome_port', 9222)}"


def chrome_running(config: dict) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(cdp_url(config) + "/json/version", timeout=1):
            return True
    except OSError:
        return False


def start_chrome(config: dict, url: str) -> None:
    import subprocess
    subprocess.Popen([
        chrome_path(),
        f"--user-data-dir={profile_dir(config)}",
        f"--remote-debugging-port={config.get('chrome_port', 9222)}",
        "--no-first-run", "--no-default-browser-check",
        url,
    ])


def connect_chrome(p, config: dict):
    """Connect to the Vinted Chrome (start it if it is not open)."""
    import time
    if not chrome_running(config):
        start_chrome(config, config["domain"])
        for _ in range(30):
            time.sleep(0.5)
            if chrome_running(config):
                break
        else:
            raise SystemExit(tr("Chrome does not respond on the debug port."))
    browser = p.chromium.connect_over_cdp(cdp_url(config))
    return browser, browser.contexts[0]


def is_logged_in(page, config: dict) -> bool:
    page.goto(config["domain"] + "/items/new", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    if "/items/new" not in page.url:
        return False
    return page.locator("input[type=file]").count() > 0
