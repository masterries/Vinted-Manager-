// The page skeleton: every top-level element of the page, with the ids and classes of the old hub.html
// (see "DOM skeleton" in docs/FRONTEND.md). Re-renders on every notify() of the store.
import { html, useLayoutEffect } from "../lib/preact.js";
import { useStore } from "../state/index.js";
import { Header } from "./Header.js";
import { JobPanel } from "./JobPanel.js";
import { Lightbox } from "./Lightbox.js";
import { SettingsDialog } from "./SettingsDialog.js";
import { Toast } from "./Toast.js";
import { ListingsMain } from "../views/listings/ListingsMain.js";
import { ActionsBar } from "../views/listings/ActionsBar.js";
import { PricesView } from "../views/prices/PricesView.js";
import { StatsView } from "../views/stats/StatsView.js";

export function App() {
  const s = useStore();
  // Prices and Statistics use the full width: body.table-mode hides list, detail, action bar and filter.
  // As before, only once the data is loaded: until then (or if the first load fails) the layout with #detail shows.
  const table = !!s.data && (s.view === "prices" || s.view === "stats");
  useLayoutEffect(() => { document.body.classList.toggle("table-mode", table); });
  return [
    html`<${Header} />`,
    html`<${ListingsMain} />`,
    html`<section id="table-view" class="table-view" hidden=${!table}>${!table ? null
      : s.view === "prices" ? html`<${PricesView} />` : html`<${StatsView} />`}</section>`,
    html`<${ActionsBar} />`,
    html`<${JobPanel} />`,
    html`<${Lightbox} />`,
    html`<${SettingsDialog} />`,
    s.settingsOpen ? null : html`<${Toast} />`,   // inside the dialog while it is open (SettingsDialog)
  ];
}
