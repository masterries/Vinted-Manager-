// Loading data, reloading when listings.json changed elsewhere, navigation (view, filter, selection, chart metric).
import { t } from "../i18n.js";
import * as api from "../api.js";
import { remember } from "../lib/storage.js";
import { state, notify } from "./store.js";
import { byFolder, visibleListings } from "./selectors.js";
import { saveNow, saveSettled, hasPending, resetServerState } from "./save.js";
import { applySettings, settingsGeneration } from "./settings.js";
import { toast } from "./ui.js";

// GET /api/data (after saving what is pending). Returns true on success.
export async function load() {
  try { await saveNow(); } catch (e) { return false; }
  const gen = settingsGeneration();
  let data;
  try {
    data = await api.fetchData();
  } catch (e) {
    state.loadError = e.message;
    notify();
    return false;
  }
  state.data = data;
  state.loadError = null;
  if (gen === settingsGeneration()) applySettings(data.settings, { render: false });   // not if a local change started or ended meanwhile
  resetServerState(data.listings);
  if (!state.current || !byFolder(state.current)) state.current = (visibleListings()[0] || data.listings[0] || {}).folder || null;
  notify();
  return true;
}

// Header button "Reload"
export async function reload() {
  if (await load()) toast(t("Reloaded"));
}

// Did someone else (e.g. Claude) change listings.json? Then reload when the tab regains focus.
export async function checkVersion() {
  if (!state.data || document.hidden || hasPending()) return;
  try {
    const { version } = await api.fetchVersion();
    if (version !== state.data.version) {
      await saveSettled();
      if (!hasPending() && await load()) toast(t("The listings were changed elsewhere and have been reloaded."));
    }
  } catch (e) { /* server briefly unreachable */ }
}

let statsLoading = null;
// GET /api/stats. Concurrent calls share one request.
export function loadStats() {
  if (statsLoading) return statsLoading;
  statsLoading = (async () => {
    try { state.stats = await api.fetchStats(); }
    catch (e) { state.stats = { history: [] }; toast(t("Could not load statistics: {error}", { error: e.message })); }
    finally { statsLoading = null; }
    notify();
  })();
  return statsLoading;
}

// Switch view ("listings" | "prices" | "stats"), optionally selecting a listing (e.g. "open in the hub")
export function showView(view, folder) {
  state.view = view;
  remember("view", view);
  if (folder) state.current = folder;
  if (view === "stats") loadStats();
  notify();
  window.scrollTo({ top: 0 });
}

// Select a listing (list click, arrow keys, after approve). mobile: the phone layout switches to the detail.
export async function selectListing(folder, mobile) {
  try { await saveNow(); } catch (e) { return; }
  state.current = folder;
  state.loadError = null;
  if (mobile) document.body.classList.add("mobile-detail");
  notify();
  window.scrollTo({ top: 0 });
}

// Phone layout: back from the detail to the list
export function showList() {
  document.body.classList.remove("mobile-detail");
}

export function setFilter(filter) {
  state.filter = filter;
  remember("filter", filter);
  notify();
}

// Statistics charts: "views" | "favorites"
export function setMetric(metric) {
  state.metric = metric;
  remember("metric", metric);
  notify();
}
