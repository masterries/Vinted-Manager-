// Polling /api/status (Chrome open? job running/finished? listings.json changed? settings changed in another tab?)
// and the jobs that run in the Vinted Chrome (fill, fill_approved, prices, stats).
import { t } from "../i18n.js";
import * as api from "../api.js";
import { state, notify } from "./store.js";
import { saveNow, saveSettled, hasPending } from "./save.js";
import { applySettings, settingsGeneration } from "./settings.js";
import { load, loadStats } from "./data.js";
import { toast } from "./ui.js";

let pollTimer = null;

export function schedulePoll(ms) {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(pollStatus, ms);
}

// Every 5 s (1.5 s while a job runs). Reloads the data when listings.json changed, unless the user is typing.
// Re-renders only when something it shows changed (Chrome open/closed, the job status, the settings): most polls
// change nothing, and a full re-render of the Statistics view every few seconds is wasted work. An unchanged job
// status keeps the old object, so the job panel scrolls its log only when a new status arrived.
export async function pollStatus() {
  let next = 5000;
  try {
    const wasRunning = !!(state.live.job && state.live.job.running);
    const gen = settingsGeneration();
    const st = await api.fetchStatus();
    let changed = false;
    if (st.chrome !== state.live.chrome) { state.live.chrome = st.chrome; changed = true; }
    if (JSON.stringify(st.job) !== JSON.stringify(state.live.job)) { state.live.job = st.job; changed = true; }
    if (st.job && st.job.running && state.jobDismissed) { state.jobDismissed = false; changed = true; }   // closing a finished job's window does not hide the next job
    // settings: not if a local change started or ended meanwhile
    if (gen === settingsGeneration() && applySettings(st.settings, { render: false })) changed = true;
    if (changed) notify();
    if (st.job.running) next = 1500;
    if (wasRunning && !st.job.running && state.view === "stats") loadStats();
    const typing = document.activeElement && document.activeElement.matches("input, textarea, select");
    if (state.data && st.version !== state.data.version && !hasPending() && !typing && !document.hidden) {
      await saveSettled();
      if (await load() && wasRunning && !st.job.running) toast(t("Job finished, data updated."));
    }
  } catch (e) { /* server briefly unreachable */ }
  schedulePoll(next);
}

// name: "fill" (folder required) | "fill_approved" | "prices" | "stats"
export async function startJob(name, folder) {
  try {
    await saveNow();
    state.live.job = await api.postJob(name, folder);
    state.jobDismissed = false;
    notify();
    schedulePoll(1500);
  } catch (e) { toast(e.message); }
}

export async function stopJob() {
  try {
    state.live.job = await api.postJobStop();
    notify();
  } catch (e) { toast(e.message); }
}

// "Close" on a finished job's panel
export function dismissJob() {
  state.jobDismissed = true;
  notify();
}

export async function openChrome() {
  try {
    await api.postChromeOpen();
    toast(t("Opening the Vinted Chrome. The first time, log in there yourself."));
    setTimeout(pollStatus, 2500);
  } catch (e) { toast(t("Error: {error}", { error: e.message })); }
}
