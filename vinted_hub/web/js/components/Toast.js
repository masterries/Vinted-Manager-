// Short message at the bottom (state.toast, shown for 3.2 s by toast() in state/ui.js).
// App renders it at the end of the page while the settings dialog is closed, SettingsDialog inside the dialog while
// it is open (a modal dialog covers everything outside it). Never both at once, so the id stays unique.
import { html } from "../lib/preact.js";
import { useStore } from "../state/index.js";

export function Toast() {
  const s = useStore();
  return html`<div id="toast" class="toast" role="status" hidden=${!s.toast.visible}>${s.toast.text}</div>`;
}
