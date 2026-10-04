/* ---------- Editing & saving ----------
   Edits change the listing object in the store at once (so every re-render shows them) and go into a queue:
   save() collects changes per listing, saveNow() sends them; sends run one after another so an older state never
   overtakes a newer one. Each send carries `base` - the values the page started from (serverState). If someone else
   (e.g. Claude) changed a field meanwhile, the server answers 409 and the page keeps both versions (state.conflicts):
   the other version in the field, the user's input in the conflict box until "Keep my version" or "Discard".
   Edits typed while a rejected request was under way were typed on top of the rejected text: they join the conflict
   too (conflict() below) instead of going out against the new base and silently overwriting the other change. */
import { t } from "../i18n.js";
import * as api from "../api.js";
import { num, clone } from "../util/format.js";
import { missingItems } from "../domain/listing.js";
import { state, notify } from "./store.js";
import { byFolder, currentListing, visibleListings } from "./selectors.js";
import { toast } from "./ui.js";

let pending = {};                    // unsaved changes {folder, fields}
let queued = [];                     // batches handed to the chain, not sent yet (a 409 can still take fields out)
let saveTimer = null;
let saveChain = Promise.resolve();
let serverState = {};                // folder -> values as last delivered by the server (base against overwriting)
let statusBusy = false;

export const hasPending = () => !!pending.fields;
export const saveSettled = () => saveChain.catch(() => {});     // resolves when all queued sends are done (never rejects)

export function rememberServer(listing) { serverState[listing.folder] = clone(listing); }
export function resetServerState(listings) { serverState = {}; listings.forEach(rememberServer); }
export const serverValue = (folder, field) => (serverState[folder] || {})[field];

const same = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const hasConflicts = (folder) => Object.keys(state.conflicts[folder] || {}).length > 0;

// Text next to the title ("Saving …"); re-translated on every render from the code
export function showSaveState(code, folder) {
  state.saveState = { folder: folder || state.current, code };
  notify();
}

export function save(changes, immediate, folder) {
  const target = folder || state.current;
  if (pending.folder && pending.folder !== target) saveNow().catch(() => {});
  pending.folder = target;
  pending.fields = Object.assign(pending.fields || {}, changes);
  showSaveState("unsaved", target);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveNow().catch(() => {}), immediate ? 0 : 700);
}

// Sends what is pending; returns the chain (rejects if the last send failed).
export function saveNow() {
  clearTimeout(saveTimer);
  if (pending.fields && pending.folder) {
    const batch = { folder: pending.folder, changes: pending.fields };
    pending = {};
    queued.push(batch);
    showSaveState("saving", batch.folder);
    saveChain = saveChain.catch(() => {}).then(() => send(batch));
  }
  return saveChain;
}

async function send(batch) {
  queued = queued.filter((b) => b !== batch);
  if (!Object.keys(batch.changes).length) return;     // all of it joined a conflict while it waited (conflict())
  const base = {};
  const old = serverState[batch.folder] || {};
  for (const k of Object.keys(batch.changes)) if (k in old) base[k] = old[k];
  try {
    const fresh = await api.postListing(batch.folder, batch.changes, base);
    applyServerState(fresh, Object.keys(batch.changes));
    if (pending.fields) notify();
    else showSaveState(hasConflicts(batch.folder) ? "conflict" : "saved", batch.folder);   // an open conflict box still needs a decision
  } catch (e) {
    if (e.status === 409 && e.data && e.data.listing) {
      conflict(batch, e.data.listing, e.data.conflicts || []);
      return;
    }
    pending = { folder: batch.folder, fields: Object.assign(batch.changes, pending.fields || {}) };
    showSaveState("failed", batch.folder);
    toast(t("Saving failed: {error}", { error: e.message }));
    throw e;
  }
}

// 409: the server rejected the whole request because `conflicts` were changed elsewhere; `fresh` is its listing.
function conflict(batch, fresh, conflicts) {
  const folder = batch.folder;
  const before = serverState[folder] || {};
  // what the server has differently from what this page's edits were typed against
  const changed = new Set(conflicts);
  for (const k of Object.keys(fresh)) if (!same(fresh[k], before[k])) changed.add(k);
  const rejected = {}, retry = {};
  for (const k of Object.keys(batch.changes)) {
    if (conflicts.includes(k)) rejected[k] = batch.changes[k];
    else if (!changed.has(k)) retry[k] = batch.changes[k];   // not saved either, but nobody else changed it
  }
  // Edits of this listing made while the request was under way - waiting batches (oldest first), then what is still
  // pending - were typed on top of the rejected text. For fields the server changed they join the conflict (the newest
  // text wins; one equal to the server's value needs no decision) and are not sent.
  const later = queued.filter((b) => b.folder === folder).map((b) => b.changes);
  if (pending.folder === folder && pending.fields) later.push(pending.fields);
  for (const changes of later) {
    for (const k of Object.keys(changes)) {
      delete retry[k];                                       // a newer edit of the field goes out anyway
      if (!changed.has(k)) continue;
      if (same(changes[k], fresh[k])) delete rejected[k];
      else rejected[k] = changes[k];
      delete changes[k];
    }
  }
  if (pending.fields && !Object.keys(pending.fields).length) { pending = {}; clearTimeout(saveTimer); }
  state.conflicts[folder] = Object.assign(state.conflicts[folder] || {}, rejected);
  // Show the other version only where the server changed something; other unsent edits stay in their fields
  const i = byFolder(folder);
  if (i) for (const k of changed) if (k in fresh) i[k] = fresh[k];
  rememberServer(fresh);
  if (Object.keys(retry).length) requeue(folder, retry);
  state.saveState = { folder, code: "conflict" };
  notify();
}

// Puts fields back into the queue and sends them soon, without overwriting newer pending edits of the same listing.
function requeue(folder, fields) {
  if (pending.folder && pending.folder !== folder) saveNow().catch(() => {});
  pending = { folder, fields: Object.assign({}, fields, pending.fields || {}) };
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveNow().catch(() => {}), 0);
}

// Takes over what the server decided (status, photo list, …) without touching fields the user may still be typing in.
export function applyServerState(fresh, fields) {
  const i = byFolder(fresh.folder);
  if (i) for (const k of ["status", "updated_at", "photos", "_folder_missing", "_all_photos", "_missing_photos"]) i[k] = fresh[k];
  const server = serverState[fresh.folder] || (serverState[fresh.folder] = {});
  for (const k of fields.concat(["status", "photos"])) server[k] = clone(fresh[k]);
  if (fresh._version && state.data) state.data.version = fresh._version;
}

const isNumberField = (key) => key === "price" || key === "min_price";
const sendable = (key, value) => !isNumberField(key) || !String(value).trim() || Number.isFinite(num(value));

// Detail form of the selected listing (old onEdit). Invalid numbers are kept in the field but not sent
// (they would block saving the other fields).
export function editField(key, value) {
  const i = currentListing();
  if (!i || i[key] === value) return;
  i[key] = value;
  if (sendable(key, value)) save({ [key]: value });
  else notify();
}

// Price/minimum price typed in the Prices table (any listing)
export function editPrice(folder, key, value) {
  const i = byFolder(folder);
  if (!i) return;
  i[key] = value;
  if (sendable(key, value)) save({ [key]: value }, false, folder);
  else notify();
}

// A price suggestion button (detail or Prices table)
export function setPrice(folder, value) {
  const i = byFolder(folder);
  if (!i) return;
  i.price = value;
  save({ price: value }, true, folder);
}

// New photo order/selection of a listing
export function setPhotos(folder, photos) {
  const i = byFolder(folder);
  if (!i) return;
  i.photos = photos;
  save({ photos }, true, folder);
}

// Conflict box: keep my rejected input (saves it again, now against the new base) or drop it
export function adoptConflict(folder, field) {
  const k = state.conflicts[folder];
  if (!k || !(field in k)) return;
  const value = k[field];
  delete k[field];
  const i = byFolder(folder);
  if (i) i[field] = value;
  save({ [field]: value }, true, folder);
}

export function discardConflict(folder, field) {
  const k = state.conflicts[folder];
  if (!k) return;
  delete k[field];
  notify();
}

// Status buttons and Ctrl+Enter. After approving, jumps to the next listing still to review.
export async function setStatus(status) {
  const i = currentListing();
  if (!i || statusBusy) return;
  if (status === "approved" && missingItems(i).length) { toast(t("Fill in the missing details first.")); return; }
  statusBusy = true;
  try {
    await saveNow();
    const fresh = await api.postListing(i.folder, { status }, { status: serverValue(i.folder, "status") });
    applyServerState(fresh, ["status"]);
  } catch (e) {
    toast(e.status === 409 ? t("The status was changed elsewhere in the meantime. Please reload.") : t("Status not changed: {error}", { error: e.message }));
    return;
  } finally {
    statusBusy = false;
  }
  if (status === "approved") {
    toast(t("Approved ✓"));
    const candidates = visibleListings().filter((x) => x.folder !== i.folder && (x.status === "new" || x.status === "on_hold"));
    const next = candidates.find((x) => x.folder > i.folder) || candidates[0];
    if (next) state.current = next.folder;
    window.scrollTo({ top: 0 });
  }
  notify();
}
