// main.layout of the Listings view: the list (aside#list) and the detail (section#detail).
// Both containers always exist; in the other views they render nothing (body.table-mode hides the layout).
// The detail is keyed by the selected listing: a listing switch (list click, ↑/↓, the jump after approving,
// "open in the hub") rebuilds it like the old page did, so focus returns to the page and no field, button or open
// <details> of the previous listing is reused for the next one. Polls, language switches, 409s and answers keep
// the key, so typing, focus and caret survive them.
import { html } from "../../lib/preact.js";
import { t } from "../../i18n.js";
import { useStore } from "../../state/index.js";
import { List } from "./List.js";
import { Detail } from "./Detail.js";

export function ListingsMain() {
  const s = useStore();
  return html`<main class="layout">
    <aside id="list" class="list" aria-label=${t("Listings")}><${List} /></aside>
    <section id="detail" class="detail"><${Detail} key=${s.current || ""} /></section>
  </main>`;
}
