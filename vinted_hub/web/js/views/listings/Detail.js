// Detail of the selected listing (right column; on phones the second screen): header with title and save state,
// conflict box, "Still missing", hints, photos, fields, photo analysis, keyboard hints.
// Shows the load error instead when /api/data failed.
import { html } from "../../lib/preact.js";
import { t } from "../../i18n.js";
import { LOCKED, missingItems } from "../../domain/listing.js";
import { useStore, currentListing, showList } from "../../state/index.js";
import { StatusPill } from "../../components/Badges.js";
import { Conflicts } from "./Conflicts.js";
import { MissingBox } from "./MissingBox.js";
import { Photos } from "./Photos.js";
import { Fields } from "./Fields.js";
import { Analysis } from "./Analysis.js";

// Text next to the title; re-translated on every render
const SAVE_TEXT = { unsaved: () => t("Unsaved …"), saving: () => t("Saving …"), saved: () => t("Saved ✓"),
  conflict: () => t("Conflict, see above"), failed: () => t("Not saved!") };

function SaveState({ saveState, current }) {
  const show = !!saveState.code && saveState.folder === current && !!SAVE_TEXT[saveState.code];
  const error = show && (saveState.code === "conflict" || saveState.code === "failed");
  return html`<div id="save-state" class=${error ? "save-state error" : "save-state"}>${show ? SAVE_TEXT[saveState.code]() : ""}</div>`;
}

export function Detail() {
  const s = useStore();
  if (s.loadError) return html`<div class="box missing">${t("Could not load data: {error}", { error: s.loadError })}</div>`;
  if (!s.data || s.view !== "listings") return null;
  const i = currentListing();
  if (!i) return null;
  const locked = LOCKED.has(i.status);
  const missing = missingItems(i);
  const missingFields = new Set(locked ? [] : missing.map((x) => x.field).filter(Boolean));
  const noText = !i.title && !i.description && !(i.hints || []).length;
  const reviewing = i.status === "new" || i.status === "on_hold";
  return [
    html`<div class="detail-header">
      <button class="btn back" data-key="detail-back" onClick=${showList}>${t("← List")}</button>
      <div class="title-block">
        <div class="folder">${i.folder}</div>
        <h2 id="header-title">${i.title || t("(no title yet)")}</h2>
      </div>
      <${StatusPill} status=${i.status} style="margin-top:6px" />
      <${SaveState} saveState=${s.saveState} current=${s.current} />
    </div>`,
    noText ? html`<div class="box info">${t("There is no listing text for this folder yet. Tell Claude, for example: “Analyse the new folders and fill in the listings.”")}</div>` : null,
    html`<${Conflicts} listing=${i} conflicts=${s.conflicts} />`,
    html`<${MissingBox} listing=${i} missing=${missing} drafts=${s.questionDrafts} />`,
    (i.hints || []).length ? html`<div class="box hint"><h3>${t("Hints from the photo analysis")}</h3>
      <ul>${i.hints.map((x) => html`<li>${x}</li>`)}</ul></div>` : null,
    locked ? html`<div class="box info">${t("This listing is already on Vinted. Changes here don’t change it there, so the fields are locked.")}</div>` : null,
    html`<${Photos} listing=${i} locked=${locked} missing=${missingFields.has("photos")} />`,
    html`<${Fields} listing=${i} conditions=${s.data.conditions} packages=${s.data.packages} settings=${s.settings} missing=${missingFields} />`,
    html`<${Analysis} listing=${i} />`,
    html`<div class="keys"><kbd>↑</kbd> <kbd>↓</kbd> ${t("previous/next listing")}${reviewing
      ? [" · ", html`<kbd>${t("Ctrl")}</kbd>`, "+", html`<kbd>Enter</kbd>`, " ", t("approve")] : null}</div>`,
  ];
}
