// Shown after a save was rejected (409) because the listing was changed elsewhere meanwhile (e.g. by Claude):
// the new version is in the fields, the user's rejected input is listed here to keep or discard.
import { html } from "../../lib/preact.js";
import { t, displayValue } from "../../i18n.js";
import { fieldName } from "../../domain/listing.js";
import { adoptConflict, discardConflict } from "../../state/index.js";

export function Conflicts({ listing: i, conflicts }) {
  const k = conflicts[i.folder];
  if (!k || !Object.keys(k).length) return null;
  return html`<div class="box missing">
    <h3>${t("This listing was changed elsewhere in the meantime (e.g. by Claude)")}</h3>
    <div style="margin-bottom:6px">${t("The new version is shown above. Your input was not saved:")}</div>
    ${Object.entries(k).map(([field, value]) => html`<div key=${field} style="margin:8px 0">
      <strong>${fieldName(field) + ": "}</strong>
      <span style="white-space:pre-wrap">${Array.isArray(value) ? value.join(", ") : String(displayValue(field, value) ?? "")}</span>
      <div class="tools">
        <button class="btn small" data-key=${`conflict-keep-${field}`} onClick=${() => adoptConflict(i.folder, field)}>${t("Keep my version")}</button>
        <button class="btn small" data-key=${`conflict-discard-${field}`} onClick=${() => discardConflict(i.folder, field)}>${t("Discard")}</button>
      </div>
    </div>`)}
  </div>`;
}
