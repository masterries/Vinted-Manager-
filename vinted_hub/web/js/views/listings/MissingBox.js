// div#missing-box: the red "Still missing" box (open questions with answer buttons, missing fields as links to the
// field) or the green "Everything needed is filled in", then the answered questions (with "Undo" for the last one)
// and the tips. Empty for listings already on Vinted.
import { html } from "../../lib/preact.js";
import { t, tn, fmtNum } from "../../i18n.js";
import { LOCKED, tips } from "../../domain/listing.js";
import { undoAnswer } from "../../state/index.js";
import { Question } from "./Question.js";

// Scroll to a field and put the cursor into it (link in the "Still missing" box)
function focusField(field) {
  const el = document.querySelector(`#detail [data-field="${field}"]`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  const input = el.querySelector("input, select, textarea");
  if (input) input.focus({ preventScroll: true });
}

// Stable keys for the list items, independent of the UI language (questions by id, other items by field)
function withKeys(items) {
  const seen = {};
  return items.map((x) => {
    const base = x.question ? `q:${x.question.id}` : `f:${x.field || "-"}`;
    seen[base] = (seen[base] || 0) + 1;
    return { x, key: seen[base] > 1 ? `${base}:${seen[base]}` : base };
  });
}

// missing: the result of missingItems(listing)
export function MissingBox({ listing: i, missing, drafts }) {
  if (LOCKED.has(i.status)) return html`<div id="missing-box"></div>`;
  const tipList = tips(i);
  const answered = (i.questions || []).filter((q) => q.answer);
  const last = (i.history || []).slice(-1)[0];
  return html`<div id="missing-box">
    ${missing.length
      ? html`<div key="missing" class="box missing"><h3>${t("Still missing ({n})", { n: fmtNum(missing.length) })}</h3>
          <ul class="questions">${withKeys(missing).map(({ x, key }) => html`<li key=${key}>${x.question ? html`<${Question} listing=${i} question=${x.question} drafts=${drafts} />`
            : x.field ? html`<a onClick=${() => focusField(x.field)}>${x.text}</a>` : x.text}</li>`)}</ul>
        </div>`
      : html`<div key="ok" class="box ok"><h3 style="margin:0">${t("✓ Everything needed is filled in")}</h3></div>`}
    ${answered.length
      ? html`<details class="answered">
          <summary>${tn(answered.length, "{n} question answered", "{n} questions answered")}</summary>
          <ul>${answered.map((q) => html`<li key=${q.id}>${`${q.question} → ${q.answer}`}${q.note
            ? html`<span style="color:var(--red)">${` (${q.note})`}</span>` : null}${last && last.question === q.id
            ? [" ", html`<button class="btn small" data-key="undo-answer" onClick=${() => undoAnswer(i.folder)}>${t("Undo")}</button>`] : null}</li>`)}</ul>
        </details>`
      : null}
    ${tipList.length ? html`<div class="box hint"><h3>${t("Tips")}</h3><ul>${tipList.map((x) => html`<li>${x}</li>`)}</ul></div>` : null}
  </div>`;
}
