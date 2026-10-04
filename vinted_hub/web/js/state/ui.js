// Small page-level UI state: toast, lightbox, clipboard.
import { t } from "../i18n.js";
import { photoOrder } from "../domain/listing.js";
import { state, notify } from "./store.js";
import { byFolder } from "./selectors.js";

let toastTimer = null;

// Shows a short message for 3.2 s (components/Toast.js renders it - inside the settings dialog while that is open).
export function toast(text) {
  state.toast = { text, visible: true };
  notify();
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    state.toast = { text: state.toast.text, visible: false };
    notify();
  }, 3200);
}

export function openLightbox(folder, file) {
  const i = byFolder(folder);
  if (!i) return;
  state.lightbox = { open: true, folder, index: photoOrder(i).indexOf(file) };
  notify();
}

export function stepLightbox(step) {
  const i = byFolder(state.lightbox.folder);
  if (!i) return;
  const all = photoOrder(i);
  if (!all.length) return;
  state.lightbox = Object.assign({}, state.lightbox, { index: (state.lightbox.index + step + all.length) % all.length });
  notify();
}

export function closeLightbox() {
  state.lightbox = Object.assign({}, state.lightbox, { open: false });
  notify();
}

export async function copyText(text, label) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.style.cssText = "position:fixed;opacity:0";
    ta.value = text;
    document.body.append(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  toast(t("{name} copied", { name: label }));
}
