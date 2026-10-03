# Vinted Hub – How it works

Deutsche Fassung: [GUIDE.md](GUIDE.md)

## For you

1. **Take photos** of each pair (side view, size label/insole, brand, outsole, flaws) and drop them, unsorted, into `0_input_photos`.
2. **Tell Claude:** “New photos are in 0_input_photos, please analyse.”
3. **Open the hub:** double-click `Start Hub.bat` → http://127.0.0.1:8765
   - **Listings** view: answer the questions in the red **Still missing** box with one click, reorder the photos.
   - **Prices** view: set your prices (click the research **Suggestion** or one of Vinted's values to use it, or type your own).
     **Fetch Vinted prices** reads Vinted's price suggestion (it saves nothing on Vinted).
   - **Approve ✓** → **Fill in on Vinted** (including the parcel size: Medium, Large for very big shoes) → check the form in the
     Vinted Chrome and click “Save draft”/“Upload” yourself. The hub then detects on its own whether the listing is online or a draft.
4. **Vinted Chrome:** `Vinted Login.bat` (or **Open** at the top right of the hub). Log in yourself once and keep the window open.
5. **Statistics:** **Fetch statistics** (top right or in the **Statistics** view) reads views and favourites
   of all your Vinted listings (read-only) and stores every fetch in `data\stats.json`. Sold items are set to “Sold” automatically.

Pace: rather list 3–6 pairs a day (Vinted favours fresh listings, and it looks less automated).

## Settings

Open **Settings** in the hub's header. Each setting has two values, English or German:

| Setting | What it does |
|---|---|
| **Interface language** | Language of the hub (buttons, messages, job logs) and of the texts Claude writes for you in **new** analyses: questions, answer buttons, hints, price reasoning. |
| **Title language** | Language Claude uses for the titles of new listings (English e.g. “… Size 39”, German “… Gr. 39”). |
| **Description language** | Language Claude uses for the descriptions of new listings – always one language, never bilingual. |

- Your choice is saved in `data\settings.json` (only on your computer). Without a choice of your own, everything is English.
- Existing listings do **not** change. The dialog shows how many listings not yet on Vinted (to review, on hold, approved)
  are written in another language. The hub does not translate by itself – if you want them rewritten, ask Claude, e.g.
  “Please rewrite the open listings in English.”
- Questions and hints in existing listings stay in the language they were written in.

## For Claude (technical)

- Find new photos + contact sheet: `.venv\Scripts\python.exe tools\contact_sheet.py` → look at `data\analysis\_contact_*.jpg`, group pairs,
  **copy** the photos to `data\items\<NN_name>\` (continue the numbering; the originals stay in `0_input_photos`).
- Read the settings: `.venv\Scripts\python.exe -m vinted_hub settings` (one JSON line; change them with `settings set key=value`).
- Analysis: saved workflow `vinted-analysis` (`.claude\workflows\vinted-analysis.js`),
  args = `{settings: <JSON from above>, items: [{folder, photos:[...]}]}`. Writes `data\analysis\<folder>.json` in the hub's format
  (title/description in the chosen languages, the description in one language only, fields `title_language` /
  `description_language`, questions with text replacements, `suggested_price`; `price` stays empty).
- Check: `tools\check_listing.py <file.json>` · Import: `tools\import_listings.py` (never overwrites edited listings).
- Never overwrite `data\listings.json` from an old copy – only via `vinted_hub.core.update_fields` / `import_listings.py` (the hub may run at the same time).
- Upload commands (`python -m vinted_hub fill`, `fill-approved`, `prices`) work through the Vinted Chrome (CDP port 9222) and never save anything on Vinted by themselves.
- Code and data are English (e.g. status `new`/`approved`/`draft`/`sold`); the interface is bilingual (English in the code,
  German in the `DE` dictionaries). Mapping and the rewrite procedure: `CLAUDE.md` (German).
