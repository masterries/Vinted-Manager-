# Vinted Hub

A small, local sales hub for selling your own items on Vinted. It was built for listing a few dozen pairs of shoes on vinted.lu.

Drop in photos → Claude analyses them (brand, size, condition, heel height, price suggestion, bilingual listing text) →
you review and answer open questions with one click → the Vinted upload form is filled in automatically →
**you press “Upload” yourself** → views and favourites are tracked over time.

![Hub – listings with one-click questions](docs/images/hub-listings.png)

> The hub's user interface is in German (“Vinted Zentrale”). Code, file names, commands and data keys are English.
> German button labels are quoted below with a translation.

## Features

| Area | What it does |
|---|---|
| **Analysis** | Photos (including iPhone HEIC) are grouped into pairs. For each pair, one agent reads labels, boxes and soles, estimates heel height and shape, researches prices and writes the listing. A second agent then tries to refute every claim. Nothing is guessed: uncertain facts are marked in the text and turned into questions. |
| **Listings** | Status workflow: to review → approved → draft → online → sold. A red “missing” box (“Fehlt noch”) shows **one-click question buttons**. Each answer rewrites the title and the bilingual description (English + German) for you, so you never edit the text by hand. You can also reorder photos, pick the cover photo and undo answers. |
| **Prices** | All pairs in one table: the research-based suggestion and **Vinted's own price recommendation** (bargain / optimal / premium). Adopt one with a click or type your own price. |
| **Fill in Vinted** | Fills photos, title, description, category, brand, size, condition, colours, material and price in your own logged-in Chrome. Runs one listing at a time or all approved listings in a row. A human always presses submit. |
| **Statistics** | Reads views and favourites of all your listings (read-only) and stores every fetch. Shows KPI tiles, a trend chart and a per-listing comparison, with a table view. Sold items are detected automatically. |

| Prices | Vinted form, filled in automatically |
|---|---|
| ![Prices](docs/images/hub-prices.png) | ![Filled-in Vinted form](docs/images/vinted-form.png) |

![Statistics](docs/images/hub-stats.png)

<details>
<summary>Statistics in dark mode</summary>

![Statistics, dark mode](docs/images/hub-stats-dark.png)
</details>

## How it works

```
0_input_photos/ ──► Claude Code analysis workflow ──► data/listings.json
                    (one analysis + one review agent per pair)
                                                          │
                              local hub (127.0.0.1:8765) ◄┘
                              review · answer questions · set prices · approve
                                                          │
             your own Chrome (logged in by you, attached via CDP) ◄┘
             form filled by Playwright ──► you click “Upload”
                                                          │
                              statistics: views / favourites over time ◄┘
```

- **No bot browser:** a browser launched by Playwright was blocked by Vinted's bot detection. The hub therefore starts a normal Chrome with its own profile. You log in yourself, and the scripts attach to that window over the Chrome DevTools Protocol.
- **Lightweight on purpose:** the server uses only the Python standard library plus Pillow. The UI is one HTML file with vanilla JavaScript and SVG charts, with no build step and no framework.
- **Safe with parallel edits:** writes use a file lock, atomic replace with a backup, and per-field conflict detection. Editing in the hub while a job runs does not lose changes.

## Setup (Windows)

Requirements: Python 3.9+ and Google Chrome.

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No separate Playwright browser download is needed; the scripts use your installed Chrome.
The analysis step needs [Claude Code](https://claude.com/claude-code). The hub itself runs without it.

## Usage

1. Run **`Vinted Login.bat`**. It opens a normal Chrome window with a dedicated profile. Log in to Vinted yourself once and keep the window open.
2. Put your unsorted photos into **`0_input_photos/`** and tell Claude Code (opened in this folder) to analyse them, e.g. “New photos are in 0_input_photos, please analyse”. The agent instructions live in [`CLAUDE.md`](CLAUDE.md).
3. Run **`Start Hub.bat`**. It opens the hub at http://127.0.0.1:8765.
4. Answer the questions, set your prices and approve the listing (“Freigeben”). Then click “In Vinted ausfüllen” (fill in Vinted) and submit the form yourself in the Vinted Chrome.
5. Now and then click “Statistik abrufen” (fetch statistics).

Every step also works from the command line:

```bat
.venv\Scripts\python.exe -m vinted_hub serve            :: start the hub (--no-browser to skip opening it)
.venv\Scripts\python.exe -m vinted_hub login            :: open the Vinted Chrome
.venv\Scripts\python.exe -m vinted_hub fill <folder>    :: fill the upload form for one listing
.venv\Scripts\python.exe -m vinted_hub fill-approved    :: fill all approved listings, one after another
.venv\Scripts\python.exe -m vinted_hub prices           :: read Vinted's price recommendation (saves nothing on Vinted)
.venv\Scripts\python.exe -m vinted_hub stats            :: fetch views and favourites
.venv\Scripts\python.exe -m vinted_hub explore          :: dump the upload form (when Vinted changes it)
```

A short day-to-day guide for the seller, in German, is in [`docs/GUIDE.md`](docs/GUIDE.md).

## Project structure

```
vinted_hub/                Python package – python -m vinted_hub <command>
  core.py                  config, paths, data read/write (with file lock), photo handling
  chrome.py                start / attach to the Vinted Chrome via CDP
  form.py                  fill the Vinted upload form, read the price recommendation
  commands.py              CLI commands (login, fill, fill-approved, prices, stats, explore)
  server.py                local hub server (standard library + Pillow)
  web/hub.html             hub UI (single file, vanilla JS, SVG charts)
tools/                     contact_sheet.py · check_listing.py · import_listings.py · explore_dropdowns.py
.claude/workflows/         vinted-analysis.js – analysis workflow for Claude Code
config.json                domain, ports, listing language (en+de), folders
Start Hub.bat              start the hub
Vinted Login.bat           open the Vinted Chrome
data/                      all personal data (not in git)
docs/                      GUIDE.md (German user guide) · images/ (screenshots)
CLAUDE.md / AGENTS.md      instructions for AI coding agents
```

## Configuration

`config.json`:

| Key | Meaning |
|---|---|
| `domain` | Vinted site, e.g. `https://www.vinted.lu` |
| `listing_language` | `en+de` = English title, description in English and German |
| `input_folder` / `data_folder` | drop folder for new photos / folder for all personal data |
| `hub_port` / `chrome_port` | port of the hub (8765) / remote-debugging port of the Vinted Chrome (9222) |
| `max_photos` | maximum number of photos per listing |

## Privacy

All personal data stays **local** and is excluded via `.gitignore`:

- photos (`0_input_photos/`, `data/items/`)
- listings (`data/listings.json`) and statistics (`data/stats.json`)
- analysis results (`data/analysis/`) and the archive (`data/archive/`)
- debug output (`data/debug/`)
- the browser profile with your Vinted login (`data/browser-profile/`)

Before upload, photos are rotated, resized and saved **without GPS metadata**.

## Disclaimer

Vinted's terms of service prohibit automated tools. This project is meant for small-scale private use and is deliberately gentle:

- it uses a real browser that you log in to yourself;
- it fills one listing at a time;
- it **never submits anything on its own**;
- it fetches statistics only when you click the button.

Use it at your own risk. This project is not affiliated with Vinted.
