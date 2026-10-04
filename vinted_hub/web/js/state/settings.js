/* ---------- Settings (data/settings.json via /api/settings) ----------
   They also arrive with /api/data and every /api/status poll, so other tabs follow a change.
   settingsGen is bumped when a local change starts and when it ends: settings in an answer to a request sent before
   that (GET /api/settings, /api/status, /api/data) are stale and must not undo the newer local state, not even briefly.
   Callers that read settings from such an answer remember settingsGeneration() before sending and compare after. */
import { t, setLanguage } from "../i18n.js";
import * as api from "../api.js";
import { state, notify } from "./store.js";
import { toast } from "./ui.js";

let settingsBusy = 0;
let settingsChain = Promise.resolve();
let settingsGen = 0;

export const settingsGeneration = () => settingsGen;

// Takes over settings from the server. Invalid values are ignored; while a local change is running only with force.
// opts.render === false: no notify (the caller renders anyway). Returns true if something changed.
export function applySettings(incoming, opts) {
  opts = opts || {};
  if (!incoming || typeof incoming !== "object" || (settingsBusy && !opts.force)) return false;
  const next = Object.assign({}, state.settings);
  for (const k of Object.keys(next)) if ((state.choices[k] || []).includes(incoming[k])) next[k] = incoming[k];
  if (!Object.keys(next).some((k) => next[k] !== state.settings[k])) return false;
  state.settings = next;
  setLanguage(next.ui_language);   // html lang + tab title, only if the language really changed
  if (opts.render !== false) notify();
  return true;
}

// gen: settingsGen when the request was sent (none = the answer to the page's own POST, always current)
function readSettingsResponse(r, gen) {
  if (!r || typeof r !== "object") return;
  if (r.choices && typeof r.choices === "object") {
    const next = {};
    for (const k of Object.keys(state.choices)) next[k] = Array.isArray(r.choices[k]) && r.choices[k].length ? r.choices[k] : state.choices[k];
    state.choices = next;
  }
  if (r.info && typeof r.info === "object") state.settingsInfo = r.info;
  // a later queued change wins, and an answer to a request sent before the latest local change is stale
  if (r.settings && settingsBusy <= 1 && (gen === undefined || gen === settingsGen)) applySettings(r.settings, { force: true, render: false });
}

// GET /api/settings (when the dialog opens, and after a failed change). Returns false if it failed.
export async function refreshSettings() {
  const gen = settingsGen;
  let ok = true;
  try { readSettingsResponse(await api.fetchSettings(), gen); state.settingsError = null; }
  catch (e) { state.settingsError = e.message; ok = false; }
  notify();
  return ok;
}

// Every change is saved right away; the page switches immediately and follows the server's answer.
export function changeSetting(key, value) {
  if (state.settings[key] === value) return;
  const before = Object.assign({}, state.settings);
  settingsBusy++; settingsGen++;
  applySettings(Object.assign({}, state.settings, { [key]: value }), { force: true });
  settingsChain = settingsChain.catch(() => {}).then(async () => {
    try {
      readSettingsResponse(await api.postSettings({ [key]: value }));
      notify();
      toast(t("Saved"));
    } catch (e) {
      // back to what the server has (or what was shown before), then report in that language
      if (!(await refreshSettings()) && settingsBusy <= 1) applySettings(before, { force: true });
      toast(t("Not saved: {error}", { error: e.message }));
    } finally {
      settingsBusy--; settingsGen++;
    }
  });
}

// The dialog component (components/SettingsDialog.js) calls showModal()/close() when settingsOpen changes.
export function openSettings() {
  if (state.settingsOpen) return;
  state.settingsOpen = true;
  notify();
  refreshSettings();
}

export function closeSettings() {
  if (!state.settingsOpen) return;
  state.settingsOpen = false;
  notify();
}
