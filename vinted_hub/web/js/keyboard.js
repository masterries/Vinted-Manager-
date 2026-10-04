// Global keyboard shortcuts:
//   settings dialog open: nothing (the dialog handles its keys, Esc closes it)
//   photo viewer open:    Esc closes, ← / → previous / next photo
//   Ctrl/⌘ + Enter:       approve the selected listing (only in the Listings view with the detail visible, status
//                         "to review" or "on hold"; no key repeat). In Prices/Statistics the hidden listing stays as it is.
//   ↑ / ↓ (not in a field): previous / next listing of the list
import { state, currentListing, visibleListings, selectListing, setStatus, closeLightbox, stepLightbox } from "./state/index.js";

function onKeyDown(e) {
  const dialog = document.getElementById("settings");
  if (state.settingsOpen || (dialog && dialog.open)) return;
  if (state.lightbox.open) {
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowRight") stepLightbox(1);
    if (e.key === "ArrowLeft") stepLightbox(-1);
    return;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    const i = currentListing();
    const detail = document.getElementById("detail");
    // In table mode only the parent main.layout is display:none, so #detail alone would still count as visible
    const visible = state.view === "listings" && !!detail && getComputedStyle(detail).display !== "none";
    if (!e.repeat && i && visible && (i.status === "new" || i.status === "on_hold")) setStatus("approved");
    return;
  }
  if (e.target && e.target.closest && e.target.closest("input, textarea, select")) return;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    const list = visibleListings();
    const idx = list.findIndex((i) => i.folder === state.current);
    const next = list[idx + (e.key === "ArrowDown" ? 1 : -1)];
    if (next) { e.preventDefault(); selectListing(next.folder); }
  }
}

export function installKeyboard() {
  document.addEventListener("keydown", onKeyDown);
}
