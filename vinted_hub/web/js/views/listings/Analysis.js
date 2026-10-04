// "How was this recognised?" - the evidence the photo analysis wrote (folded <details>; stays open across re-renders).
import { html } from "../../lib/preact.js";
import { t } from "../../i18n.js";

function row(name, value) {
  if (!value || !(Array.isArray(value) ? value.length : String(value).trim())) return null;
  return html`<div style="margin:8px 0"><strong>${name + ": "}</strong>${Array.isArray(value)
    ? html`<ul style="margin:4px 0;padding-left:20px">${value.map((w) => html`<li>${w}</li>`)}</ul>`
    : String(value)}</div>`;
}

export function Analysis({ listing: i }) {
  const a = i.analysis;
  if (!a) return null;
  return html`<details class="card">
    <summary style="cursor:pointer;font-weight:600">${t("How was this recognised? (photo analysis)")}</summary>
    <div style="font-size:13.5px;color:var(--muted);margin-top:8px">
      ${row(t("Model"), a.model)}${row(t("Brand"), a.brand_evidence)}${row(t("Size"), a.size_evidence)}
      ${row(t("Condition"), a.condition_reasoning)}${row(t("Flaws"), a.flaws)}${row(t("Heel/shape"), a.shape_evidence)}
      ${row(t("Price sources"), a.price_sources)}
    </div>
  </details>`;
}
