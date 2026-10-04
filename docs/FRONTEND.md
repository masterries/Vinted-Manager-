# Frontend guide – the hub web UI

The hub page ("Vinted Hub" / "Vinted Zentrale") is a small **Preact + htm** app, split into ES modules under
`vinted_hub/web/`. The library is **vendored** (one file, `web/vendor/preact-htm.js`): **no npm, no build step**.
The browser loads the modules as they are; the Python server (`vinted_hub/server.py`) serves them.

It replaced the single file `web/hub.html` (≈1,960 lines of CSS + vanilla JS). Behaviour, texts, DOM ids/classes,
keyboard shortcuts and localStorage keys stayed the same; the few deliberate differences are listed at the end.

Contents: 1 File layout · 2 How it works · 3 Interface contract · 4 Server contract · 5 Old → new mapping ·
6 Conventions · 7 Testing · 8 Areas and the translation checker · 9 Deliberate differences

---

## 1. File layout

```
vinted_hub/web/
  index.html                 shell: <head> (meta, favicon "data:,", title, CSS links, 2 scripts), <body><div id="app">
  vendor/
    preact-htm.js            htm 3.1.1 "preact/standalone" (Preact 10 + htm), unmodified - import only via js/lib/preact.js
    LICENSE-htm.txt          htm licence (Apache 2.0)
    LICENSES.md              what is vendored, Preact MIT notice
  css/                       loaded in this order by index.html; rule text copied unchanged from hub.html
    base.css                 tokens (light + dark), reset, .btn .chip .pill .s-* badges .lang-badge .box .card .tools .segmented kbd
    layout.css               #app, header, .layout/.list/.detail grid, .actions bar, table mode, phone breakpoints
    listings.css             .item, detail header, save state, questions/answered, photos, fields grid
    tables.css               .view-header, .table-frame, .table (Prices + Statistics)
    stats.css                --viz-* tokens, tiles, metric row, chart cards, .viz-tip
    overlays.css             lightbox, toast, job panel, settings dialog
  js/
    app.js                   entry: test bridge, then (not on file://) initLanguage(), render(<App/>), keyboard, window listeners, load() + poll
    file-hint.js             CLASSIC script (not a module): the "don't open as a file" hint on file:// (modules are blocked there)
    test-bridge.js           window globals of the old page for the browser regression tests, incl. lineChart()/metrics() (see 2.6)
    keyboard.js              global shortcuts (↑/↓, Ctrl+Enter, lightbox keys)
    api.js                   all HTTP calls + imageUrl()
    i18n.js                  t, tn, setLanguage, displayValue, locale, fmtNum, … (merges the DE dictionaries)
    i18n/
      de.core.js             German texts: shell, header, values, field names, saving, jobs, settings, shared components
      de.listings.js         German texts: Listings view
      de.prices.js           German texts: Prices view
      de.stats.js            German texts: Statistics view
    lib/
      preact.js              re-export of the vendored library (the standalone build has no Fragment: return an array)
      storage.js             remember(name, value) - localStorage "vh_<name>", never throws
      testHooks.js           exposeFunctions(), exposeState() - put names on window for tests/console
    util/
      format.js              num, euro, decimalText, timeText, dateText, clone, fmtNum, webUrl (safe link targets from data)
    domain/
      listing.js             LOCKED, NOT_ON_VINTED, EMPTY, PLACEHOLDER, missingItems, tips, fieldName, photoOrder, languageMismatch
    state/
      store.js               the state object, notify(), subscribe(), useStore()
      selectors.js           listings(), byFolder(), visibleListings(), currentListing(), jobRunning()
      data.js                load, reload, checkVersion, loadStats, showView, selectListing, showList, setFilter, setMetric
      save.js                save queue + 409 conflicts, editField, editPrice, setPrice, setPhotos, setStatus, conflicts
      listingActions.js      answer, undoAnswer, question drafts, preparePhotos
      status.js              pollStatus (5 s), jobs (start/stop/dismiss), openChrome
      settings.js            applySettings, changeSetting (settingsGen guard), refreshSettings, open/closeSettings
      ui.js                  toast, lightbox, copyText
      index.js               barrel: import everything above from one place
    components/              shared, view-independent
      App.js                 page skeleton (all top-level elements, see 2.4), body class "table-mode"
      Header.js              h1, view switch, header stats, reload, settings button, --header-h, hosts Filter + ChromeStatus
      ChromeStatus.js        dot + "Vinted Chrome open/closed", Open / Fill in all approved / Fetch statistics buttons
      Filter.js              status chips (#filter)
      JobPanel.js            #job
      Lightbox.js            #lightbox
      Toast.js               #toast
      SettingsDialog.js      native <dialog id="settings">
      icons.js               GearIcon
      inputs.js              TextInput, TextArea - fields that keep caret and unsaved text across re-renders
      Badges.js              StatusPill, Delta
      PriceChoices.js        price suggestion buttons (detail + Prices table)
    views/
      listings/              ListingsMain (main.layout = List + Detail keyed by the listing), ActionsBar, List, Detail,
                             Conflicts, MissingBox, Question, Photos, Fields, Analysis (one exported component per file)
      prices/
        PricesView.js
      stats/
        StatsView.js         the view: header, tiles, metric switch, chart cards, table (no test code)
        metrics.js           metrics(): names/colours of "views" and "favorites"
        chartUtils.js        niceScale, textWidth, truncate, AXIS_FONT
        ChartCard.js         card with measured width, tooltip host
        LineChart.js, BarChart.js, Sparkline.js, Tiles.js, StatsTable.js
```

Inside a view the file split is free; the entry modules, exports and DOM contracts below are fixed.

---

## 2. How it works

### 2.1 Boot (`js/app.js`)

```js
import "./test-bridge.js";
import { html, render } from "./lib/preact.js";
import { initLanguage } from "./i18n.js";
import { App } from "./components/App.js";
import { installKeyboard } from "./keyboard.js";
import { load, pollStatus, checkVersion, hasPending, saveNow } from "./state/index.js";

if (location.protocol !== "file:") {             // a module cannot `return` at the top level, hence the block
  initLanguage();                                 // html lang + tab title (once)
  render(html`<${App} />`, document.getElementById("app"));
  installKeyboard();
  window.addEventListener("focus", checkVersion);
  document.addEventListener("visibilitychange", checkVersion);
  window.addEventListener("beforeunload", (e) => { if (hasPending()) { saveNow().catch(() => {}); e.preventDefault(); e.returnValue = ""; } });
  load().then(() => pollStatus());
}
```

On `file://` Chromium refuses ES modules; `file-hint.js` (a classic script) shows the hint instead (a console error
about the blocked module is expected there). Browsers that do run modules from `file://` (Firefox, depending on its
file-URI setting) stop at the protocol check, so the app never renders next to the hint.

### 2.2 Rendering model: one store, full re-render

- **One plain state object** (`state/store.js`). Domain objects (the listings in `state.data`) are **mutable**, exactly
  as in the old page: an edit writes `listing[key] = value` at once. Only modules in `js/state/` change state; each
  change ends with `notify()`.
- **Components** call `const s = useStore()` and re-render after every `notify()`. Preact batches these into one
  render pass per tick (microtask). The whole tree re-renders; for ≈100 listings this is cheap.
- **No selectors with equality checks, no `memo`/`useMemo` keyed on store objects.** Because objects are mutated in
  place, reference equality says nothing. Derive values during render (`missingItems(i)` etc.).
- Why this pattern: it maps 1:1 onto the old page (globals + `renderX()` → `state` + `notify()`), keeps the subtle
  logic (save queue, 409, settingsGen) a straight port, and lets the regression tests mutate state through the bridge.
  Context + useReducer would force immutable updates everywhere for no gain at this size.
- Local, purely visual state (chart tooltip, measured width) stays in the component (`useState`).
- The status poll (every 5 s, 1.5 s during a job) calls `notify()` only when something it shows changed – Chrome
  open/closed, the job status (compared as JSON; an unchanged job keeps its object), the settings – so an idle page does
  not re-render the whole tree (the Statistics view: two charts, tiles, table) every few seconds. A data reload notifies
  through `load()`. Bar labels are cut to width through a small cache (`truncate()` in `chartUtils.js`, ≤ 500 entries).

### 2.3 Unsaved input, focus and caret across re-renders

- Unsaved text lives in the **data** (`listing.notes`, `state.questionDrafts[key]`), so any re-render (5 s poll,
  language switch, another field's save) renders it again.
- Text fields use **`components/inputs.js`** (`TextInput`, `TextArea`). They do not pass `value` to Preact; a layout
  effect writes the DOM value only when it differs from the store **and** the field is not being edited. While the
  field is focused, the user's text (or its formatted form) is kept; a real change from outside (answer applied,
  409 conflict, other listing selected) replaces it and keeps the caret where possible. `format` (e.g. `decimalText`)
  applies only while not focused. `onValue(text)` must update the store synchronously (call an action).
- **Stable structure = same DOM nodes = focus survives.** Always give list items a `key` (folder, file, field key,
  `q:<folder>:<id>`, `data-key`), render `null` for absent optional parts instead of shifting siblings, and keep the
  element type of a slot stable. Never re-create the tree on purpose (no `key` changes on language switch).
- **The other way round: when a slot gets a different meaning, change its key on purpose**, so a focused element never
  silently takes over another listing's field or another action (the old page rebuilt these parts and focus fell back to
  `<body>`):
  - the detail is keyed by the selected listing (`ListingsMain.js`: `<${Detail} key=${s.current || ""} />`). A listing
    switch (list click, ↑/↓, the jump after approving, "open in the hub") rebuilds it; polls, language switches, 409s and
    answers keep the key, so typing, focus and caret survive them. Removed images keep downloading in the browser, so
    the Photos card drops their `src` when it unmounts (otherwise holding ↓ through listings whose previews are not
    generated yet piles up slow image requests that block the browser's few connections to the hub);
  - the action bar's buttons are keyed by listing + `data-key` (`ActionsBar.js`), the job panel's Cancel/Close by
    `data-key` (`JobPanel.js`): after a status button is pressed by keyboard, or after ↓, a second Enter does nothing.
- `<select>`: controlled is fine (`value=${…}`), there is no caret. Preact only sets the `value` property, so the options
  also get `defaultSelected=${o === value}` to keep the `selected` attribute of the old page (Fields.js).
- `<details>` keep their open/closed state while the same listing is shown (Preact does not touch `open` unless you pass
  it); a listing switch rebuilds the detail (all closed again, focus returns to the page, as before).

### 2.4 DOM skeleton (rendered by `App`, ids/classes unchanged from hub.html)

```
div#app (display: contents)
  header.header
    h1#app-name                                   t("Vinted Hub")
    nav#view-switch.segmented[aria-label=t("View")]     3 buttons [aria-pressed][data-key=view-<k>] (after data loaded)
    div#header-stats.header-stats                 "{n} pairs · …" with <b> numbers (after data loaded)
    div.header-right
      span#chrome-status.chrome-status(.on)       ChromeStatus
      button#reload.btn[type=button][title]       t("Reload") → reload()
      button#settings-button.btn.settings-button[type=button][aria-haspopup=dialog][title][aria-label]
                                                  GearIcon + span.label-text t("Settings") → openSettings()
    nav#filter.filter[aria-label=t("Filter by status")]   chips only in the Listings view
  main.layout
    aside#list.list[aria-label=t("Listings")]     items only in the Listings view
    section#detail.detail                         detail only in the Listings view (or the load error box)
  section#table-view.table-view[hidden=!table]    <PricesView/> | <StatsView/> | nothing (table = data loaded and view != listings)
  div#actions.actions[hidden]                     ActionsBar: content only in the Listings view; [hidden] when no listing
                                                  is selected (as before - note .actions{display:flex} beats [hidden])
  div#job.job[hidden]                             JobPanel (empty while hidden)
  div#lightbox.lightbox[hidden][title] > img      Lightbox
  dialog#settings.dialog[aria-labelledby=settings-title]
    div#settings-body.dialog-body                 SettingsDialog content, only while open
    div#toast.toast[role=status][hidden]          Toast as the dialog's last child WHILE OPEN (a modal dialog covers the rest)
  div#toast.toast[role=status][hidden]            Toast here while the dialog is closed (never both: the id stays unique)
```

- `body.table-mode` is set by `App` in a layout effect on every render (`view !== "listings"` **and the data is loaded**,
  as before: until then - or when the first load fails - the layout with `#detail` and its error box shows).
- `#chrome-status` stays empty until the data or a status poll arrived (as before, when the server is unreachable).
- `body.mobile-detail` (phone layout) is set by `selectListing(folder, true)` and removed by `showList()` (Back button),
  imperatively, as before; tests also toggle it directly. This is the one place where the state layer changes the DOM
  (noted in `store.js`'s header). `file-hint.js` sets it too, so the file:// hint shows on phones.
- Elements outside the current view stay in the DOM but render no content (no text in a previous language stays).

### 2.5 Language switch

`changeSetting("ui_language", x)` → `applySettings` → `setLanguage(x)` (sets `<html lang>` and the tab title **only
when it changed** – tests count lang mutations) → `notify()` → every component re-renders with the new `t()` texts.
Stored values stay English; `displayValue()` translates their display.

### 2.6 Test bridge (`js/test-bridge.js`)

The browser regression suites were written against the old page's globals. The bridge maps them onto the store:

| Global | Meaning |
|---|---|
| `D`, `STATS`, `LIVE`, `SETTINGS`, `CHOICES`, `SETTINGS_INFO`, `CONFLICTS`, `current` | getters: `state.data`, `state.stats`, `state.live`, `state.settings`, `state.choices`, `state.settingsInfo`, `state.conflicts`, `state.current` |
| `filter = x`, `metric = x` | setters (not remembered in localStorage); tests call a render function afterwards |
| `load`, `pollStatus`, `selectListing`, `showView`, `showSaveState`, `changeSetting`, `locale` | the real functions |
| `renderAll`, `renderDetail`, `renderStats` | all `notify()` (re-render after a test mutated state in place) |
| `lineChart(card, tip, points, m, width)`, `metrics()` | defined in `test-bridge.js` too: `lineChart` renders the `LineChart` component on its own (see 3.8); no view carries test code |

Keep these names working; app code never uses them.

### 2.7 Saving and 409 conflicts (`state/save.js`)

- An edit writes the listing at once and goes into `pending` (one listing at a time; 700 ms debounce, immediately on
  blur/change or for buttons). `saveNow()` turns `pending` into a batch; batches are sent strictly one after another
  (`saveChain`), each with `base` = the server's values as last delivered (`serverState`, computed when the batch is
  sent, so a second quick edit carries the first one's result and gets no false 409).
- **409** (someone else, e.g. Claude, changed a field of that request meanwhile; the server rejects the whole request):
  - the conflicting fields go into `state.conflicts[folder]` (the conflict box), the listing shows the server's version
    for every field the server changed (other unsent edits stay in their fields), `serverState` becomes the server's;
  - edits of that listing made **while the request was under way** – batches still waiting and what is still pending –
    were typed on top of the rejected text: for fields the server changed they join the conflict box (the newest text
    wins; one equal to the server's value needs no decision) and are **not** sent;
  - the request's other fields, which nobody else changed, go out again (unless a newer edit of the field follows anyway);
  - nothing re-sends the rejected text by itself: only "Keep my version" (`adoptConflict`) saves it, against the new base;
    "Discard" drops it. The save state stays "Conflict, see above" while the listing has an open conflict box.
- Covered by the browser integration checks (section 7): conflict box and Keep; an edit queued and an edit pending while
  the 409 was on its way; the retry of the other fields; another field changed elsewhere at the same time.

---

## 3. Interface contract

Import paths below are relative to `web/js/`. Components import state through `state/index.js`.

### 3.1 Store shape (`state/store.js`)

```js
state = {
  data: null | { listings: [Listing], version, statuses, conditions, packages, domain, settings },   // GET /api/data
  loadError: null | "message",          // /api/data failed: #detail shows t("Could not load data: {error}", {error})
  current: null | "folder",             // selected listing
  view: "listings" | "prices" | "stats",          // init from vh_view
  filter: "all" | status,                          // init from vh_filter
  metric: "views" | "favorites",                   // init from vh_metric
  stats: null | { member_id, history: [{ time, items: [{ id, title, url, price, views, favorites, draft, sold, reserved, hidden }] }] },
  live: { chrome: bool, job: null | { running, title, folder, log: [str], exit_code } },   // object mutated in place
  jobDismissed: bool,
  settings: { ui_language, title_language, description_language },
  choices: { ui_language: [..], title_language: [..], description_language: [..] },
  settingsInfo: null | { domain, data_folder, input_folder, hub_port, chrome_port },
  settingsError: null | "message",
  settingsOpen: bool,
  conflicts: { [folder]: { [field]: rejectedValue } },
  questionDrafts: { ["q:<folder>:<questionId>:<optionIndex>"]: "typed text" },
  saveState: { folder, code: null | "unsaved" | "saving" | "saved" | "conflict" | "failed" },
  toast: { text, visible },
  lightbox: { open, folder, index },    // index into photoOrder(listing)
}
```

Listing fields: see CLAUDE.md "Daten"; the server adds `_all_photos`, `_missing_photos`, `_folder_missing`.

Store API: `notify()`, `subscribe(fn) → unsubscribe`, `useStore() → state` (hook; re-renders on every notify).

### 3.2 Actions (all exported from `state/index.js`)

| Action | Effect |
|---|---|
| `load() → Promise<bool>` | saves pending edits, GET /api/data, takes settings (unless a local settings change started/ended meanwhile), resets the server base, keeps or picks `current`, notify |
| `reload()` | header button: `load()` + toast "Reloaded" |
| `checkVersion()` | on window focus / visibility: reloads if listings.json changed elsewhere (toast) |
| `loadStats() → Promise` | GET /api/stats → `state.stats` (error: empty history + toast); concurrent calls share one request |
| `showView(view, folder?)` | sets + remembers the view, optional `current`, loads stats for "stats", notify, scroll to top |
| `selectListing(folder, mobile?) → Promise` | saves first (aborts on failure), sets `current`, clears `loadError`, phone: adds `body.mobile-detail`, scroll to top |
| `showList()` | phone Back button: removes `body.mobile-detail` |
| `setFilter(key)` / `setMetric(key)` | set + remember (vh_filter / vh_metric), notify |
| `editField(key, value)` | detail field of the current listing (old onEdit): writes the listing, queues a save (700 ms debounce; invalid numbers are kept but not sent) |
| `editPrice(folder, key, value)` | Prices table input ("price"/"min_price"), same rules, any listing |
| `setPrice(folder, value)` | price suggestion button: writes + saves immediately |
| `setPhotos(folder, photos)` | photo order/selection: writes + saves immediately |
| `save(changes, immediate?, folder?)`, `saveNow() → Promise` | the queue itself (rarely needed directly; `onBlur` of fields calls `saveNow().catch(() => {})`); 409 handling: 2.7 |
| `hasPending()` | unsaved edits exist |
| `showSaveState(code, folder?)` | sets `state.saveState` |
| `adoptConflict(folder, field)` / `discardConflict(folder, field)` | conflict box buttons |
| `setStatus(status) → Promise` | status buttons / Ctrl+Enter on the current listing; after "approved" jumps to the next listing to review |
| `answer(folder, questionId, optionIndex, value)` | question button / typed answer (Enter or OK); the server's answer goes into the listing looked up again after the request (a reload meanwhile may have replaced `state.data`) |
| `undoAnswer(folder)` | "Undo" next to the last answered question (same rule) |
| `draftKey(folder, questionId, optionIndex)`, `setQuestionDraft(key, value)` | typed answer drafts (key = the input's data-key) |
| `preparePhotos()` | "By hand: prepare photos" (current listing) |
| `pollStatus()`, `schedulePoll(ms)` | status poll (5 s, 1.5 s while a job runs); notifies only when Chrome/job/settings changed (2.2); reloads data when the version changed and nobody is typing |
| `startJob(name, folder?)` | "fill" (folder), "fill_approved", "prices", "stats" |
| `stopJob()`, `dismissJob()`, `openChrome()` | job panel Cancel / Close, "Open" Vinted Chrome |
| `changeSetting(key, value)` | settings dialog choice: switches at once, POSTs, toast "Saved" / reverts + "Not saved: …" |
| `applySettings(incoming, {force, render})`, `refreshSettings()`, `settingsGeneration()` | settings sync internals (used by load/poll; the stale-answer guard) |
| `openSettings()` / `closeSettings()` | dialog state; the component calls `showModal()`/`close()` |
| `toast(text)` | 3.2 s message |
| `openLightbox(folder, file)`, `stepLightbox(±1)`, `closeLightbox()` | photo viewer |
| `copyText(text, label)` | Copy buttons (clipboard, fallback, toast "{name} copied") |

Selectors (read-only, safe in render): `listings()`, `byFolder(folder)`, `visibleListings()`, `currentListing()`, `jobRunning()`.

### 3.3 `api.js`

`api(path, body?)` – GET without body, POST JSON with body; throws `Error` with `.status` and `.data` (JSON error body).
`fetch` is resolved at call time (tests replace `window.fetch`); never alias it.

| Function | Request | Answer |
|---|---|---|
| `fetchData()` | GET /api/data | `{listings, version, statuses, conditions, packages, domain, settings}` |
| `fetchVersion()` | GET /api/version | `{version}` |
| `fetchStatus()` | GET /api/status | `{version, chrome, job, settings}` |
| `fetchStats()` | GET /api/stats | `{member_id, history}` |
| `fetchSettings()` | GET /api/settings | `{settings, choices, info}` |
| `postSettings(changes)` | POST /api/settings `{changes}` | like GET |
| `postListing(folder, changes, base)` | POST /api/listing `{base, folder, changes}` | listing + `_version`; 409 `{error, conflicts, listing}` |
| `postAnswer(folder, question, option, value)` | POST /api/answer | listing + `_version` |
| `postAnswerUndo(folder)` | POST /api/answer/undo | listing + `_version` |
| `postPreparePhotos(folder)` | POST /api/photos/prepare | `{count}` |
| `postJob(name, folder)` | POST /api/job | job status |
| `postJobStop()` | POST /api/job/stop | job status |
| `postChromeOpen()` | POST /api/chrome/open | `{running}` |
| `imageUrl(folder, file, width)` | – | `/image/<folder>/<file>?w=<width>` (360 thumbnails, 1600 lightbox) |

Only `js/state/*` calls the fetch functions; components call actions. `imageUrl` is fine anywhere.

### 3.4 `i18n.js`

| Export | |
|---|---|
| `t(text, vars?)` | translate + fill `{placeholders}`; returns a string, or an array of strings/vnodes if a var is a vnode (`t("{n} pairs", {n: html\`<b>…</b>\`})`) |
| `tn(n, one, many, vars?)` | plural; sets `{n}` to `fmtNum(n)` unless `vars.n` is given |
| `getLanguage()`, `LANGUAGES` | "en" / "de" |
| `setLanguage(lang) → bool` | persists vh_lang, html lang + title only if changed. Called by `applySettings` – components never call it |
| `initLanguage()` | once at boot |
| `locale()`, `fmtNum(v)`, `langName(code)` | "en-GB"/"de-DE", localised number, "English"/"German" in the UI language |
| `valueLabels(key)`, `displayValue(key, v)`, `statusLabel(status)` | display of stored English values (status, condition, package, brand) |

DE dictionaries: `i18n/de.<area>.js` = `export default { "English": "Deutsch", … };`, one entry per line, `//` comments
allowed, same `{placeholders}`. `i18n.js` merges core, listings, prices, stats. A text lives in **exactly one** file.

### 3.5 `util/format.js` and `domain/listing.js`

- format: `num(v)` (parses "12,50 €", "12,-"), `euro(v)` ("–" for empty), `decimalText(v)` (comma in German),
  `timeText(iso)`, `dateText(text)`, `clone(x)`, `fmtNum`, `webUrl(url)` (the url if it is http(s), else `undefined` =
  no `href`; every link built from data goes through it).
- domain: `LOCKED` (draft/online/sold → read-only), `NOT_ON_VINTED`, `EMPTY`, `PLACEHOLDER`, `openQuestions(i)`,
  `required()`, `textChecks()`, `fieldName(key)`, `missingItems(i)` → `[{field, text} | {field, question}]`,
  `tips(i)`, `photoOrder(i)` (chosen then unused photos), `languageMismatch(listings, settings)` → `{title, description}`.

### 3.6 Shared components (props)

| Component | Props | Renders |
|---|---|---|
| `TextInput` (`components/inputs.js`) | `value`, `onValue(text)`, `format?`, `type?` + any attribute (`id`, `class`, `placeholder`, `readonly`, `disabled`, `inputmode`, `aria-label`, `data-key`, `onBlur`, `onChange`, `onKeyDown`, …) | `<input>` |
| `TextArea` | same (no `type`) | `<textarea>` |
| `StatusPill` (`components/Badges.js`) | `status` + any attribute (`style`, `title`) | `span.pill.s-<status>` with the translated status |
| `Delta` | `now`, `old` | `span.badge-ok|badge-missing` "+3"/"-1", or nothing |
| `PriceChoices` (`components/PriceChoices.js`) | `listing` | array of ≤4 `button.btn.small[data-key=price-choice:<folder>:<suggested|bargain|optimal|premium>]` → `setPrice()`; the caller supplies the container (`div.tools` / `div.choices`) |
| `GearIcon` (`components/icons.js`) | – | the 16 px gear SVG (`aria-hidden`, `focusable=false`) |

### 3.7 Listings view and shell – behaviour to keep

Ported one to one from the old `render*` functions (texts, classes, inline styles, `data-key`s, titles, aria). Notably:
- List items: `div.item[data-folder][aria-current]`, keyed by folder; badge "{n} missing"/"complete"; stats pill; price pill.
- Detail: `h2#header-title` (live while typing), `div#save-state.save-state(.error)` from `state.saveState` when
  `folder === current` (texts: Unsaved …/Saving …/Saved ✓/Conflict, see above/Not saved!), `div#missing-box`.
- Fields: `id="f-<key>"`, `[data-field=<key>]`, class `is-missing` from `missingItems()` (not for locked listings),
  counter `span#count-<key>`, `label.label[for=f-<key>]` with the language badge `.lang-badge` (title/description),
  Copy `button[data-key=copy-<key>]` → `copyText(currentValue, label)`; `onBlur`/`onChange` → `saveNow()`.
- Questions: `input.question-input[data-key=q:<folder>:<id>:<idx>]` (Enter answers), OK button `…:ok`, disabled when locked.
- Photos card `[data-field=photos]`, buttons `photo-use|fwd|off|back-<file>`, image click → `openLightbox`.
- Actions bar per status (`status-<status>`, `prepare-photos`, `fill-one`, links `a.btn.small` "View on Vinted ↗" /
  "Open the Vinted form ↗" with `target=_blank rel=noopener`, `href` through `webUrl()`). Buttons keyed by
  `<folder>|<data-key>` (2.3). Job panel: Cancel `[data-key=job-stop]` / Close `[data-key=job-close]`, keyed by data-key.
- Settings dialog: ids `settings-title`, `set-ui`, `set-texts`, `set-info`, `set-<key>-label`; rows `div.set-row`
  (label span + `div.segmented[role=group][aria-labelledby]`), buttons `[data-key=set-<key>-<value>][aria-pressed]`,
  UI language names in their own language with `lang` attribute, choices in `state.choices` order; ✕ `[data-key=set-close]`;
  on open: `showModal()`, focus the pressed UI-language button, `refreshSettings()`; Esc, ✕ and a backdrop click
  (pointerdown **and** click on the dialog element itself) close; on the native `close` event: `closeSettings()` and
  focus `#settings-button`.
- Keyboard (`keyboard.js`): nothing while the dialog is open; lightbox open: Esc closes, ←/→ step; Ctrl/⌘+Enter:
  approve the current listing if the Listings view is shown, `#detail` is visible and status is new/on_hold (no repeat;
  in table mode only the parent `main.layout` is hidden, so `#detail` alone would still count as visible); ↑/↓ outside
  inputs: previous/next visible listing.
- Header: `ResizeObserver` on `.header` sets `--header-h` on `<html>`.

### 3.8 Seams: shell ↔ Prices/Statistics

**App ↔ Prices/Statistics.** `App` renders
`<section id="table-view" class="table-view" hidden=${!table}>` (`table` = data loaded and `view !== "listings"`) and
inside it `<${PricesView} />` when `view === "prices"`, `<${StatsView} />` when `view === "stats"`.

- `views/prices/PricesView.js`: `export function PricesView()` – no props; `useStore()`; returns the section's
  children (`div.view-header` + `div.table-frame > table.table`). Uses `editPrice`, `saveNow` (on blur),
  `startJob("prices")` (`button[data-key=fetch-prices]`), `showView("listings", folder)` (title link),
  `PriceChoices`, `StatusPill`, `TextInput` (`format=${decimalText}`, `inputmode="decimal"`,
  `data-key=price-input:<folder>:<key>`, class `empty` when the price is missing, `readonly` when locked).
- `views/stats/StatsView.js`: `export function StatsView()` – no props; `useStore()`; if `state.stats` is null:
  shows `div.help` "Loading …" and calls `loadStats()` **in an effect** (never during render). Uses `setMetric`
  (`button[data-key=metric-<k>]`), `startJob("stats")`, `showView("listings", folder)`, `Delta`, `imageUrl`, `webUrl`
  (item links).
  Charts: same geometry as before (line chart H = 210, x-axis labels at `y = H - 9`, label overlap rule, crosshair;
  bars 28 px rows; hit areas are `rect[fill=transparent]`; tooltip `div.viz-tip[hidden]` inside `div.chart-card`);
  redraw on width change ≥ 8 px (debounced 120 ms); no horizontal page scroll at 375 px.
- Test hooks (defined in `js/test-bridge.js`, which imports `LineChart`, `lineTip`, `placeTip` and `metrics`; the views
  carry no test code): `exposeFunctions({ lineChart, metrics })` from `lib/testHooks.js`, where
  `metrics()` returns `{ views: {name, unit, total, perListing, color: "var(--viz-1)"}, favorites: {…, color: "var(--viz-2)"} }`
  and `lineChart(card, tip, points, m, width)` returns a detached `<svg>` element of the line chart for
  `points = [{time: ms, value}]` (renders the `LineChart` component into a temporary `div` and returns its first element; the crosshair works and
  the tooltip goes into `tip`, placed inside `card`). So `LineChart` takes everything through props (no `useStore`) and
  its root is the `<svg>`.
- Global listeners live in `app.js`/`keyboard.js` (keydown, focus, visibilitychange, beforeunload) and `Header.js`
  (ResizeObserver for `--header-h`); the views add none except a `ResizeObserver` inside each chart card.

**CSS.** Shell: `base.css`, `layout.css`, `overlays.css`; Listings: `listings.css`; Prices and the statistics table:
`tables.css`; Statistics: `stats.css`. New rules go into the file of their area. `index.html` links all six; the order
matters for the cascade (rule text and order are those of the old `<style>`, plus `#app { display: contents }`).

**Strings.** `de.core.js` (shell, shared components, stored values, field names), `de.listings.js`, `de.prices.js`,
`de.stats.js`. Reuse an existing key from any file; a new key goes into the file of the area that uses it (a key in two
files is an error).

**State.** Everything that changes state or talks to the server lives in `js/state/*` (+ `api.js`); views only read the
store and call actions. Shared helpers: `lib/*`, `util/*`, `domain/*`, `components/inputs.js`, `Badges.js`,
`PriceChoices.js`. `test-bridge.js` only maps the old globals and the chart hooks for the tests (2.6).

---

## 4. Server contract (`vinted_hub/server.py`)

| Request | Response |
|---|---|
| `GET /`, `GET /index.html` | `web/index.html`, `text/html; charset=utf-8`, plus `Content-Security-Policy` and `X-Frame-Options: DENY` (below) |
| `GET /css/<path>`, `/js/<path>`, `/vendor/<path>` | the file under `web/<dir>/`; only `.js` → `text/javascript; charset=utf-8`, `.css` → `text/css; charset=utf-8`; everything else (`.md`, `.txt`, `.html`, folders, missing files) → 404 JSON |
| `GET /api/...`, `/image/...`, `POST /api/...` | unchanged |

- Files are read fresh from disk on every request: `Cache-Control: no-cache` + `ETag` (`"<mtime_ns>-<size>"`),
  `If-None-Match` → 304, `X-Content-Type-Options: nosniff`. An edited file applies on the next page reload.
- Path traversal (`static_path()` / `_bad_segment()` in server.py): every URL segment is decoded **on its own** (an encoded
  `%2f` cannot create a new segment); a segment that is empty, `.` or `..`, contains `/`, `\`, `:` or NUL, ends with a dot
  or a space (Windows would drop them, so `app.js.` would alias `app.js`), or is a Windows device name (`CON`, `NUL.js`,
  `COM1` …) → 404. The resolved path must be inside `web/<dir>` and end in `.js`/`.css`. Covered by
  `tools/test_server_static.py` (72 trick paths, Host check, MIME types, ETag/304, page security headers).
- The page itself (only the HTML response, also its 304; `PAGE_HEADERS` in server.py) carries
  `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
  connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'` and `X-Frame-Options: DENY`. The page
  has no inline script (the old single file could not have this policy), so an accidental HTML/script injection could not
  run and no other site can frame the hub. Consequences: **no inline `<script>` and no `on…=` attributes in
  `index.html`** (the test checks both); styles may be set inline (Preact style props, `'unsafe-inline'`); images come
  from `/image/…` or `data:` (the favicon). The browser suites replace `window.fetch` at runtime through Playwright,
  which the policy does not affect. Pass `page.wait_for_function()` a function (`"() => …"`), never a bare expression
  string: Playwright evaluates expression strings with eval inside the page, which the policy blocks ('unsafe-eval').
- The Host check (DNS-rebinding protection) runs before everything, as for the API.
- `Server.request_queue_size = 128`: the page requests ~60 files at once; with the stdlib default backlog (5) Windows
  refused some connections (`ERR_CONNECTION_REFUSED`) and the app did not start.
- Why `/js/...` instead of a `/web/` prefix: the URL tree mirrors `web/`, so `index.html` uses **relative** links that
  work over http and when the file is opened directly (where `file-hint.js` must still load).
- `web/hub.html` is gone; nothing serves it.

---

## 5. Old → new mapping (every top-level item of hub.html)

| hub.html | New place |
|---|---|
| `<style>` | `css/*.css` (lines split by area, rule text unchanged; media queries split per file) |
| static body (header, main, sections, dialog, toast) | `components/App.js` + `Header.js` (same ids/classes, 2.4) |
| `const DE` | `i18n/de.core.js`, `de.listings.js`, `de.prices.js`, `de.stats.js`; file:// texts → `file-hint.js` `FILE_HINT_DE` |
| `has` | private helper in `i18n.js` / inline |
| `LANG` | `i18n.js` module state (`getLanguage()`) |
| `t`, `tn`, `locale`, `fmtNum`, `langName` | `i18n.js` (`fmtNum` re-exported by `util/format.js`) |
| `valueLabels`, `displayValue`, `statusLabel` | `i18n.js` |
| `filters` | `components/Filter.js` |
| `required`, `textChecks`, `fieldName` | `domain/listing.js` |
| `LOCKED`, `NOT_ON_VINTED`, `EMPTY`, `PLACEHOLDER` | `domain/listing.js` |
| `D`, `current`, `filter`, `view`, `STATS`, `LIVE`, `jobDismissed` | `state.data`, `.current`, `.filter`, `.view`, `.stats`, `.live`, `.jobDismissed` |
| `pending`, `saveTimer`, `saveChain` | `state/save.js` (private; `hasPending()`, `saveSettled()`) |
| `saveState` | `state.saveState` |
| `SERVER_STATE`, `rememberServer` | `state/save.js` (`serverState` private; `rememberServer`, `resetServerState`, `serverValue`) |
| `CONFLICTS`, `QDRAFTS` | `state.conflicts`, `state.questionDrafts` |
| `photosBusy` | `state/listingActions.js` (private) |
| `lightboxIndex` | `state.lightbox.index` |
| `CHOICES`, `SETTINGS`, `SETTINGS_INFO`, `SETTINGS_ERROR` | `state.choices`, `.settings`, `.settingsInfo`, `.settingsError` |
| `settingsBusy`, `settingsChain`, `settingsGen` | `state/settings.js` (private; `settingsGeneration()`) |
| `num`, `clone`, `decimalText` | `util/format.js` |
| `remember` | `lib/storage.js` |
| `h`, `setChildren`, `s`, `SVGNS` | gone – htm templates (`html` from `lib/preact.js`; SVG children inside `<svg>` are created as SVG) |
| `keepFocus` | gone – stable keyed rendering + `components/inputs.js`; keys that change on purpose where a slot changes meaning (2.3) |
| `api` | `api.js` (`api` + named endpoint functions) |
| `toast` | `state/ui.js` `toast()`; display `components/Toast.js` |
| `byFolder`, `visibleListings` | `state/selectors.js` |
| `imageUrl(i, file, w)` | `api.js` `imageUrl(folder, file, width)` |
| `openQuestions`, `missingItems`, `tips` | `domain/listing.js` |
| `load`, `checkVersion`, `loadStats`, `showView`, `selectListing` | `state/data.js` |
| `renderAll` | `components/App.js` (every `notify()` re-renders) |
| `vintedStatus` | `views/stats` |
| `timeText`, `dateText`, `euro` | `util/format.js` |
| `delta` | `components/Badges.js` `Delta` |
| `metrics`, `metric`, `swatch` | `views/stats/metrics.js` (+ `state.metric`, `setMetric`), Swatch in `views/stats` |
| `niceScale`, `textMeasurer`, `AXIS_FONT`, `textWidth`, `truncate` | `views/stats/chartUtils.js` |
| `showTip` | `views/stats/ChartCard.js` |
| `lineChart`, `barChart`, `sparkline`, `tile` | `views/stats/LineChart.js`, `BarChart.js`, `Sparkline.js`, `Tiles.js` |
| `renderStats`, `statsWidth`/`statsTimer`/ResizeObserver on #table-view | `views/stats/StatsView.js`, width measured in `ChartCard.js` |
| `renderHeader` | `components/Header.js` |
| `renderChrome` | `components/ChromeStatus.js` |
| `openChrome`, `startJob`, `stopJob`, `pollTimer`, `schedulePoll`, `pollStatus` | `state/status.js` |
| `renderJob` (+ close → `jobDismissed`) | `components/JobPanel.js` (`dismissJob()`) |
| `renderFilter` | `components/Filter.js` |
| `renderList` | `views/listings/List.js` |
| `renderDetail` | `views/listings/Detail.js` |
| `renderConflicts` (adopt/discard) | `views/listings/Conflicts.js` (`adoptConflict`, `discardConflict` in `state/save.js`) |
| `renderMissing` (+ `.is-missing` marking) | `views/listings/MissingBox.js`; `is-missing` classes computed in `Fields.js`/`Photos.js` |
| `renderQuestion` | `views/listings/Question.js` (component `Question({ listing, question, drafts })`) |
| `answer`, `undoAnswer` | `state/listingActions.js` (`answer(folder, questionId, optionIndex, value)`, `undoAnswer(folder)`) |
| `focusField` | `views/listings/MissingBox.js` (DOM helper in the click handler) |
| `renderPhotos` | `views/listings/Photos.js` (`setPhotos` in `state/save.js`) |
| `charCount`, `field`, `languageBadge`, `renderFields`, `priceHelp` | `views/listings/Fields.js` |
| `setPrice` | `state/save.js` `setPrice(folder, value)` |
| `priceChoices` | `components/PriceChoices.js` |
| `renderPrices` | `views/prices/PricesView.js` |
| `renderAnalysis` | `views/listings/Analysis.js` |
| `renderActions` | `views/listings/ActionsBar.js` |
| `onEdit`, `updateBadge` | `state/save.js` `editField(key, value)`; counter, header title and list badge follow by re-render |
| `SAVE_TEXT`, `paintSaveState` | `views/listings/Detail.js` (save state next to the title) |
| `showSaveState`, `save`, `saveNow`, `send`, `applyServerState`, `setStatus` | `state/save.js` |
| `preparePhotos` | `state/listingActions.js` |
| `copyText` | `state/ui.js` |
| `settingsDialog`, `dialogOpen` | `components/SettingsDialog.js` (element ref) / `state.settingsOpen` |
| `applySettings`, `refreshSettings`, `readSettingsResponse`, `changeSetting`, `openSettings`, `closeSettings` | `state/settings.js` |
| `applyLanguage`, `renderStatic` | `i18n.js` `setLanguage`/`initLanguage` (html lang, title); static texts are rendered by the components |
| `gearIcon` | `components/icons.js` `GearIcon` |
| `languageMismatch` | `domain/listing.js` `languageMismatch(listings, settings)` |
| `mismatchNote`, `renderSettings`, dialog listeners (close, pointerdown, click) | `components/SettingsDialog.js` |
| settings-button / reload click listeners | `components/Header.js` (`openSettings`, `reload`) |
| `showImage`, `stepImage`, lightbox click | `state/ui.js` (`openLightbox`, `stepLightbox`, `closeLightbox`), `components/Lightbox.js` |
| focus / visibilitychange → `checkVersion`, `beforeunload` | `app.js` |
| header ResizeObserver (`--header-h`) | `components/Header.js` |
| keydown handler | `keyboard.js` `installKeyboard()` |
| `applyLanguage(false)` at start, `load().then(pollStatus)` | `app.js` |
| `location.protocol === "file:"` branch | `file-hint.js` (+ the protocol check around the boot in `app.js`) |

---

## 6. Conventions

**Rules**
- Templates: `html\`…\`` from `lib/preact.js`. htm escapes text and attribute values. **Never** use
  `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write`; data never becomes HTML.
  Links built from data (`vinted_url`, a statistics item's `url`, the configured `domain`) only through `webUrl()`
  (`util/format.js`: http(s) or no `href`), with `target="_blank" rel="noopener"`.
- `index.html` stays free of inline scripts and `on…=` attributes (the page's Content-Security-Policy, section 4).
- Every visible text (also `title`, `aria-label`, `placeholder`, `alt`) through `t()`/`tn()` with **double-quoted
  literals**. English source in British spelling (favourites, colour, analyse, recognised); German in the area's
  `de.*.js`. Texts stored in listings are shown as stored – never translated.
- Components never change `state`; they call actions. Actions end with `notify()`.
- Never call an action during render; use an event handler or `useEffect`.
- Lists get `key`s; optional parts render `null`; text inputs use `TextInput`/`TextArea`. A slot that gets another
  meaning (another listing, another action) gets another `key` (2.3).
- A PascalCase file exports the component of that name (used as `html\`<${Name} …/>\``), plus at most small helpers
  that belong to it (e.g. `barTip`, `lineTip`); lowercase files (`metrics.js`, `chartUtils.js`) hold helpers only.
- Keep ids, classes, `data-key`s and aria attributes – tests and CSS rely on them.
- Python 3.9 on the server side; plain ES2020 modules in the browser (no TypeScript, no JSX, no bundler).
- Line endings LF (`.gitattributes`: `eol=lf` for py/js/css/html/md/json).

**Add a string**: write `t("Fetch failed: {error}", { error })` in the code, add
`"Fetch failed: {error}": "Abruf fehlgeschlagen: {error}",` to your area's `js/i18n/de.<area>.js`, run
`tools/check_i18n.py`. Plurals: `tn(n, "{n} item", "{n} items")` with both forms in the dictionary.

**Add an API call**: route in `server.py` (`do_GET`/`do_POST`, messages via `tr()` + `vinted_hub/i18n.py` DE) →
function in `api.js` → action in a `js/state/*.js` module (calls it, updates `state`, `notify()`, errors via `toast`)
→ export it from `state/index.js` → components call the action.

**Add a view or panel** (example: an "Attention" panel in Statistics listing items with 0–1 views and why):
1. Component in `views/<area>/` (a panel: a new file in `views/stats/`, rendered from `StatsView`).
   A whole view: `views/<name>/<Name>View.js`, exported function, `useStore()`.
2. State it needs: a field in `state/store.js` + an action (new data from the server: see "Add an API call").
3. A new view: allow it in `store.js` (initial `view` from vh_view), a button in `Header.js`'s view switch
   (`data-key=view-<name>`), render it in `App.js` inside `#table-view` (or its own container).
4. Styles in the owner's CSS file (or a new `css/<name>.css` linked in `index.html`).
5. Strings in `js/i18n/de.<name>.js` (imported and merged in `i18n.js`); run the checker.

**Update the vendored library** (no npm needed):
```powershell
# in a scratch folder
Invoke-WebRequest https://registry.npmjs.org/htm/-/htm-<version>.tgz -OutFile htm.tgz
tar -xzf htm.tgz                                  # -> package/
Copy-Item package/preact/standalone.module.js <repo>/vinted_hub/web/vendor/preact-htm.js
Copy-Item package/LICENSE <repo>/vinted_hub/web/vendor/LICENSE-htm.txt
node --input-type=module -e "import('file:///<repo>/vinted_hub/web/vendor/preact-htm.js').then(m => console.log(Object.keys(m).sort().join(' ')))"
```
The export list must still contain everything `js/lib/preact.js` re-exports. Update the version in
`vendor/LICENSES.md`, then run all tests (section 7). Never edit `preact-htm.js` by hand.

---

## 7. Testing

```powershell
# syntax of every module (fast)
Get-ChildItem vinted_hub\web\js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName }
# translations: Python tr() and web t()/tn() <-> DE dictionaries, placeholders, stale/duplicate entries, German leftovers
.venv\Scripts\python.exe tools\check_i18n.py
# static file route of the server (in-process server on a free port, empty temp data folder)
.venv\Scripts\python.exe tools\test_server_static.py
# Python lint (needs: pip install pyflakes)
.venv\Scripts\python.exe -m pyflakes vinted_hub tools
# no HTML injection sinks (must print nothing)
Get-ChildItem vinted_hub\web\js -Recurse -Filter *.js | Select-String -Pattern "innerHTML|outerHTML|insertAdjacentHTML|dangerouslySetInnerHTML|document\.write"
```

**Browser regression suites** (Playwright, headless Chrome). They are not part of the repository (they lived in the
session scratchpad of the migration): `ui_i18n_test.py` (+ `ui_fixtures.py`, 111 checks), `hubfix_ui_test.py`
(33 checks), plus the integration checks of the migration (`integ_extra_test.py`: typing across polls, save queue
order, 409, undo, keys, lightbox, localStorage, reload after a change on disk, 375 px, dark mode, file:// hint, and
since the review: edits made while a 409 was on its way, the retry of a rejected request's other fields, a listing
switch rebuilding the detail, keyed action/job buttons, Ctrl+Enter only in the Listings view, data links only http(s),
the file:// hint layout) and a DOM/pixel comparison with the old page. Always against a **throwaway copy** with its own
ports, never against the live hub (8765/9222) or real data. Keep the copy's folder path short (well under ~100
characters): preview temp files live in `data\items\<folder>\_preview\` and past Windows' 260-character limit the
`/image/…` requests fail with 500 (false test failures). Also use the function form for `wait_for_function()` (CSP, §4):

```powershell
# 1. copy the project folder (code, config.json, data\listings.json, data\stats.json, data\items)
# 2. config.json of the copy: "hub_port": 89xx, "chrome_port": 95xx
# 3. fixtures: python ui_fixtures.py <copy>   - they expect listing #12 to be "approved" and no American spelling
#    ("color", "favorite" …) in stored texts; with today's data both need a small extra step (all older listings are online)
# 4. start:  <copy> > ..\.venv\Scripts\python.exe -u -m vinted_hub serve --no-browser
# 5. run (PYTHONIOENCODING=utf-8: the suites print "✕", which a cp1252 console cannot):
$env:PYTHONIOENCODING = "utf-8"
$env:UI_TEST_BASE = "http://127.0.0.1:89xx/"; $env:UI_TEST_CHROME_PORT = "95xx"; $env:UI_TEST_COPY = "<copy folder name>"
python ui_i18n_test.py      # 111/111
python hubfix_ui_test.py    # 33/33 (fresh fixtures first)
```

Manual check after UI work: both languages, light + dark, 375 px phone width (list ↔ detail, prices, statistics,
dialog), typing in a field across a 5 s poll and a language switch (text, focus and caret stay), a 409 conflict
(edit the same field in listings.json meanwhile), keyboard only: a status button pressed with Enter, then Enter again
(nothing happens), opening `index.html` as a file (hint).

---

## 8. Areas and the translation checker

| Area | Files |
|---|---|
| Shell | `index.html`, `css/base.css`, `css/layout.css`, `css/overlays.css`, `js/app.js`, `js/keyboard.js`, `js/test-bridge.js`, `js/file-hint.js`, `js/components/*`, `js/i18n/de.core.js` |
| Shared logic | `js/state/*`, `js/api.js`, `js/i18n.js`, `js/lib/*`, `js/util/*`, `js/domain/*` |
| Listings | `js/views/listings/*`, `css/listings.css`, `js/i18n/de.listings.js` |
| Prices | `js/views/prices/*`, `css/tables.css`, `js/i18n/de.prices.js` |
| Statistics | `js/views/stats/*`, `css/stats.css` (+ `tables.css`), `js/i18n/de.stats.js` |
| Server and checks | `vinted_hub/server.py` (static route), `tools/check_i18n.py`, `tools/test_server_static.py` |

History: the split from the single file `web/hub.html` was made in one go – contracts, state layer and the CSS and
dictionary split first, then the shell + Listings and the Prices + Statistics views in parallel, then the integration
against the old page (both regression suites, the integration checks of section 7, and a DOM and pixel comparison with
the same data: every listing in both languages, Prices, Statistics and the dialog came out identical apart from the
points in section 9). `hub.html` is gone; its last version is in the git history.

`tools/check_i18n.py` (Python 3.9, run from anywhere, root = parent of `tools/`, exit 0/1, messages in German like the
other tools) replaces the two earlier checkers for `hub.html`:
- Python: every `tr("…")` literal in `vinted_hub/*.py` and `tools/*.py` ↔ `DE` in `vinted_hub/i18n.py`; only plain
  literals; placeholders equal; call kwargs = placeholders; no stale or duplicate keys; warn on German-looking literals
  outside `tr()`/DE.
- Web: every `t("…")` and both literals of `tn(n, "…", "…")` in `vinted_hub/web/js/**/*.js` (not `vendor/`, not the
  dictionaries) ↔ the merged `js/i18n/de.*.js` dictionaries; a key in two files, an empty translation, different
  `{placeholders}`, a non-English key (umlauts, „ ‚) → error; stale entries → error; `t(`/`tn(` without literals →
  error unless the line contains `i18n-dynamic` or defines them (`function t(`, `export function tn(` …); German
  characters/words in code, strings or template literals outside the dictionaries → error (allowed: "Deutsch";
  `//` comments ignored); German characters in `index.html` → error.
- Classic scripts with their own dictionary (`const FILE_HINT_DE = {` in `js/file-hint.js`) are checked against that
  dictionary only, and their texts do not count for the module dictionaries.
- Every `js/i18n/de.*.js` must be imported in `i18n.js`; a `t()`/`tn()` text with `{placeholders}` but no values is reported.

---

## 9. Deliberate differences from hub.html

- `<details>` (answered questions, photo analysis, values table) stay open across re-renders of the same listing (poll,
  language switch, typing; before: closed again whenever the detail was rebuilt). A listing switch still rebuilds the
  detail as before: all closed again, focus back on the page (2.3).
- Derived numbers (Prices totals, header counts, list badges) update while typing (before: some on the next rebuild).
- The list keeps its scroll position when you come back from Prices or Statistics (before: it started at the top again,
  because the old page rebuilt `#list`). Kept on purpose: you return to where you were.
- On `file://` the page shows the title and the hint only (no Reload/Settings buttons), in the wide detail column next
  to an empty list column as before, and now also below 820 px (before: hidden on phones); Chromium's console reports the
  blocked module script.
- The toast is rendered inside the open settings dialog instead of the same element being moved there.
- `loadStats()` shares one request when the view and `showView("stats")` ask at the same time.
- A `<div id="app">` wraps the page (CSS `display: contents`, so layout and selectors are unchanged). Measured side
  effect: inside the modal settings dialog, which sits at a fractional y position, text can rasterise 1 px lower; the
  listing-title line of the finished job panel (✓ title + Close) can likewise render 1 px higher. All layout boxes and
  text-line rectangles are identical (rasterisation only).
- The job panel scrolls its log to the end when a changed job status arrives (new log line, job finished …), not on
  unrelated re-renders (before: on every poll, so it jumped back down while you scrolled up in an unchanged log).
- The status poll re-renders only when Chrome, the job or the settings changed (2.2); nothing visible changes.
- A hidden chart tooltip keeps its last `left`/`top` inline style (invisible).
- The "Fetch statistics" button of the Statistics view follows Chrome/job changes at once (before: on the next rebuild).
- Links built from data – a statistics item's `url`, "View on Vinted ↗" (`vinted_url`), "Open the Vinted form ↗" (the
  configured domain) – get an `href` only when they are http(s) (`webUrl()`), so a `javascript:` URL can never become a
  link in the hub's origin (before: used as they were).
- The page is served with a Content-Security-Policy and `X-Frame-Options: DENY` (section 4; the old single file had an
  inline script and could not have this policy).
- Static files: trick paths (encoded separators, trailing dots or spaces, Windows device names) → 404 (section 4).

**Old bugs fixed on purpose (do not "restore parity")**
- 409 while typing: **no automatic re-send.** The old page sent the rejected value again by itself, before any click
  (overwriting the other change on disk while the field showed it and the box said "Your input was not saved"); now only
  "Keep my version" saves it. Edits typed while the rejected request was under way join the conflict box (newest text)
  instead of being sent against the new base; the request's other fields, which nobody else changed, are saved; the save
  state stays "Conflict, see above" while a conflict box is open (2.7).
- Photo and answer buttons always act on the current data, also right after a background reload (before: the photo
  buttons could save a stale photo list; an answer arriving after a reload could land in the replaced data and stay
  invisible).
- Tips and the "Still missing" list update right after a photo change (before: stale tips such as "No longer in the
  folder: …" until the next rebuild).
- Ctrl/⌘+Enter approves only in the Listings view (before: also the hidden listing while Prices or Statistics was shown,
  because only the parent of `#detail` is hidden there).

**Known limitations (unchanged from hub.html)**
- A save answer carries the file version after the write (`_version`). If someone else changed *another* listing just
  before, the page adopts that version without loading the change, so the poll does not reload it; it shows up with the
  next reload (button, or the next change on disk).
- Chart tooltips cannot be reached by keyboard; the title link in the Prices table is a non-focusable `div`.
