/* ---------- Store ----------
   One plain state object for the whole page, plus notify()/subscribe().
   - Only modules in js/state/ change `state` (actions). After a change they call notify().
   - Components read with `const s = useStore();` and re-render on every notify (no selectors, no memo on store data:
     domain objects such as listings are mutated in place, exactly like the old page did, so reference equality says nothing).
   - Unsaved input lives in the data (the listing object), so any re-render - poll, language switch - shows it again;
     text fields use components/inputs.js so a re-render never overwrites what is being typed.
   - The state layer renders nothing; besides page-level effects (window.scrollTo, reading document.activeElement or
     document.hidden) it changes the DOM in one documented place only: body.mobile-detail (the phone layout's
     list/detail switch) is toggled imperatively by selectListing()/showList() in data.js, as in the old page. */
import { useLayoutEffect, useReducer, useRef } from "../lib/preact.js";
import { remember } from "../lib/storage.js";
import { getLanguage, LANGUAGES } from "../i18n.js";

export const state = {
  data: null,              // GET /api/data: {listings, version, statuses, conditions, packages, domain, settings}
  loadError: null,         // message when /api/data failed (shown in the detail pane until the next successful load)
  current: null,           // folder of the selected listing
  view: ["prices", "stats"].includes(remember("view")) ? remember("view") : "listings",   // "listings" | "prices" | "stats"
  filter: remember("filter") || "all",                       // status filter of the list ("all" or a status)
  metric: remember("metric") === "favorites" ? "favorites" : "views",   // what the statistics charts show
  stats: null,             // GET /api/stats: {member_id, history: [...]}; null = not loaded yet
  live: { chrome: false, job: null },   // from GET /api/status (job: {running, title, folder, log, exit_code})
  jobDismissed: false,     // job panel closed after the job finished
  settings: { ui_language: getLanguage(), title_language: "en", description_language: "en" },
  choices: { ui_language: [...LANGUAGES], title_language: [...LANGUAGES], description_language: [...LANGUAGES] },
  settingsInfo: null,      // read-only info from GET /api/settings (domain, folders, ports)
  settingsError: null,     // message when GET /api/settings failed
  settingsOpen: false,     // settings dialog shown
  conflicts: {},           // folder -> {field: the user's rejected input} after a 409
  questionDrafts: {},      // "q:<folder>:<questionId>:<optionIndex>" -> typed, not yet sent answer
  saveState: { folder: null, code: null },   // code: null | "unsaved" | "saving" | "saved" | "conflict" | "failed"
  toast: { text: "", visible: false },
  lightbox: { open: false, folder: null, index: -1 },   // index into photoOrder(listing)
};

const listeners = new Set();
let version = 0;   // bumped by every notify(); lets a component notice a change that happened before it subscribed

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// Tell every subscribed component to re-render (Preact batches these into one render pass).
export function notify() {
  version++;
  for (const fn of [...listeners]) fn();
}

// Hook: returns the state object and re-renders the component after every notify().
export function useStore() {
  const [, force] = useReducer((n) => n + 1, 0);
  const seen = useRef(version);
  seen.current = version;
  useLayoutEffect(() => {
    const off = subscribe(force);
    if (seen.current !== version) force();   // a notify() between render and subscribe
    return off;
  }, []);
  return state;
}
