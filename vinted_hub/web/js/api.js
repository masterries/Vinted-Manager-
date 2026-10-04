// HTTP calls to the local server (vinted_hub/server.py). Only the modules in js/state/ call these; views call state actions.
// `fetch` is looked up at call time on purpose (tests replace window.fetch to delay answers) - never alias it.

// GET (no body) or POST JSON (body). Throws an Error with .status and .data (the JSON error body) when not ok.
export async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(d.error || r.statusText);
    err.status = r.status;
    err.data = d;
    throw err;
  }
  return d;
}

// --- reads
export const fetchData = () => api("/api/data");              // {listings, version, statuses, conditions, packages, domain, settings}
export const fetchVersion = () => api("/api/version");        // {version}
export const fetchStatus = () => api("/api/status");          // {version, chrome, job: {running, title, folder, log, exit_code}, settings}
export const fetchStats = () => api("/api/stats");            // {member_id, history: [{time, items: [{id, title, url, price, views, favorites, …}]}]}
export const fetchSettings = () => api("/api/settings");      // {settings, choices, info}

// --- writes
export const postSettings = (changes) => api("/api/settings", { changes });                       // -> like fetchSettings
// base: the values the page started from; the server answers 409 {error, conflicts: [fields], listing} if one changed meanwhile
export const postListing = (folder, changes, base) => api("/api/listing", { base, folder, changes }); // -> listing + _version
export const postAnswer = (folder, question, option, value) => api("/api/answer", { folder, question, option, value }); // -> listing + _version
export const postAnswerUndo = (folder) => api("/api/answer/undo", { folder });                    // -> listing + _version
export const postPreparePhotos = (folder) => api("/api/photos/prepare", { folder });              // -> {count}
export const postJob = (name, folder) => api("/api/job", { name, folder: folder || "" });          // -> job status
export const postJobStop = () => api("/api/job/stop", {});                                        // -> job status
export const postChromeOpen = () => api("/api/chrome/open", {});                                  // -> {running}

// Preview image of a listing photo (the server picks the nearest size: 360 or 1600)
export const imageUrl = (folder, file, width) => `/image/${encodeURIComponent(folder)}/${encodeURIComponent(file)}?w=${width}`;
