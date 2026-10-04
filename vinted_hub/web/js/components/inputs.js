/* ---------- Text fields that never fight the user ----------
   The page re-renders often (status poll every 5 s, language switch, every keystroke). A plain controlled input
   (value=${…}) would be rewritten on each render and lose the caret. These components own the DOM value instead:
   - `value` is the value in the store. onValue(text) must write it to the store synchronously (an action), so the
     store and the field agree before the next render.
   - `format` (optional, e.g. decimalText) is applied for display while the field is NOT focused.
   - While focused, the field keeps what the user typed. Only a real change from outside (answer applied, 409 conflict,
     another listing selected) replaces it; the caret is then kept where possible.
   All other props (id, class, placeholder, readonly, disabled, aria-*, data-key, onBlur, onChange, onKeyDown, …)
   go to the element unchanged. Usage:
     html`<${TextInput} id="f-title" value=${i.title} onValue=${(v) => editField("title", v)} onBlur=${…} />`
     html`<${TextInput} value=${i.price} format=${decimalText} inputmode="decimal" onValue=${…} />` */
import { html, useLayoutEffect, useRef } from "../lib/preact.js";

function useDomValue(ref, value, format) {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const raw = value === null || value === undefined ? "" : String(value);
    const shown = format ? format(raw) : raw;
    if (document.activeElement === el) {
      if (el.value === raw || el.value === shown) return;   // the user's own text (or its formatted form): leave it
      let start = null, end = null;
      try { start = el.selectionStart; end = el.selectionEnd; } catch (e) { /* no selection API */ }
      el.value = shown;
      if (start !== null) try { el.setSelectionRange(Math.min(start, shown.length), Math.min(end, shown.length)); } catch (e) { /* ignore */ }
      return;
    }
    if (el.value !== shown) el.value = shown;
  });
}

export function TextInput({ value, format, onValue, type, ...rest }) {
  const ref = useRef(null);
  useDomValue(ref, value, format);
  return html`<input type=${type || "text"} ...${rest} ref=${ref} onInput=${(e) => onValue && onValue(e.currentTarget.value)} />`;
}

export function TextArea({ value, format, onValue, ...rest }) {
  const ref = useRef(null);
  useDomValue(ref, value, format);
  return html`<textarea ...${rest} ref=${ref} onInput=${(e) => onValue && onValue(e.currentTarget.value)} />`;
}
