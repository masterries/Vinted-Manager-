// Question buttons (answer / undo), typed answer drafts, preparing photos for a manual upload.
import { t, tn } from "../i18n.js";
import * as api from "../api.js";
import { state, notify } from "./store.js";
import { byFolder, currentListing } from "./selectors.js";
import { saveNow, rememberServer } from "./save.js";
import { toast } from "./ui.js";

let answerBusy = false;
let photosBusy = false;

// Key of a typed answer draft (also the data-key of its input)
export const draftKey = (folder, questionId, optionIndex) => `q:${folder}:${questionId}:${optionIndex}`;

export function setQuestionDraft(key, value) {
  state.questionDrafts[key] = value;
  notify();
}

// Takes the server's answer for a listing. Looked up again here, after the await: a load() meanwhile (poll, window
// focus, Reload) may have replaced state.data, and the object found before the request would be a detached copy.
function takeFresh(folder, fresh) {
  const i = byFolder(folder);
  if (i) Object.assign(i, fresh);
  rememberServer(fresh);
  if (fresh._version && state.data) state.data.version = fresh._version;
}

// Applies option `optionIndex` of question `questionId` (value: the typed text for options with input)
export async function answer(folder, questionId, optionIndex, value) {
  if (answerBusy) return;
  const i = byFolder(folder);
  const q = i && (i.questions || []).find((x) => x.id === questionId);
  if (!q) return;
  const opt = q.options[optionIndex];
  if (opt.input && !String(value).trim()) { toast(t("Please enter a value first.")); return; }
  answerBusy = true;
  try {
    await saveNow();
    const fresh = await api.postAnswer(folder, questionId, optionIndex, value);
    for (const k of Object.keys(state.questionDrafts)) if (k.startsWith(`q:${folder}:${questionId}:`)) delete state.questionDrafts[k];
    takeFresh(folder, fresh);
    notify();
  } catch (e) { toast(t("Not applied: {error}", { error: e.message })); }
  finally { answerBusy = false; }
}

// Undoes the last answered question of a listing
export async function undoAnswer(folder) {
  if (!byFolder(folder)) return;
  try {
    await saveNow();
    takeFresh(folder, await api.postAnswerUndo(folder));
    notify();
  } catch (e) { toast(e.message); }
}

// "By hand: prepare photos" - copies the chosen photos without metadata and opens the folder
export async function preparePhotos() {
  const i = currentListing();
  if (!i || photosBusy) return;
  photosBusy = true;
  toast(t("Preparing photos …"));
  try {
    await saveNow();
    const r = await api.postPreparePhotos(i.folder);
    const photoCount = Number(r.count) || 0;
    toast(tn(photoCount, "{n} photo is in the opened folder as 01.jpg, without GPS data. Just drag it to Vinted.",
      "{n} photos are in the opened folder as 01.jpg, 02.jpg …, without GPS data. Just drag them to Vinted."));
  } catch (e) { toast(t("Error: {error}", { error: e.message })); }
  finally { photosBusy = false; }
}
