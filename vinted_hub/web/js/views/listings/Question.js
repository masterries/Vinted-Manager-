// One open question from the analysis, with its answer buttons. Options with `input` get a small text field
// (Enter or the button answers); what is typed is kept as a draft in the store until it is sent.
// Props: listing, question (one entry of listing.questions), drafts (state.questionDrafts).
import { html } from "../../lib/preact.js";
import { t } from "../../i18n.js";
import { LOCKED } from "../../domain/listing.js";
import { state, answer, draftKey, setQuestionDraft } from "../../state/index.js";
import { TextInput } from "../../components/inputs.js";

export function Question({ listing: i, question: q, drafts }) {
  const locked = LOCKED.has(i.status);
  return html`<div>
    <div class="question-text">${q.question}</div>
    ${q.explanation ? html`<div class="question-info">${q.explanation}</div>` : null}
    <div class="tools">${(q.options || []).map((opt, idx) => {
      const key = draftKey(i.folder, q.id, idx);
      if (!opt.input) {
        return html`<button key=${key} class="btn small" disabled=${locked} data-key=${key}
            onClick=${() => answer(i.folder, q.id, idx, "")}>${opt.label}</button>`;
      }
      return html`<span key=${key} class="question-value">
        <${TextInput} class="question-input" placeholder=${opt.placeholder || opt.label} disabled=${locked}
          aria-label=${opt.label} data-key=${key} value=${drafts[key] || ""} onValue=${(v) => setQuestionDraft(key, v)}
          onKeyDown=${(e) => { if (e.key === "Enter") answer(i.folder, q.id, idx, e.currentTarget.value); }} />
        <button class="btn small" disabled=${locked} data-key=${key + ":ok"}
          onClick=${() => answer(i.folder, q.id, idx, state.questionDrafts[key] || "")}>${opt.button || t("OK")}</button>
      </span>`;
    })}</div>
  </div>`;
}
