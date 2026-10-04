// Status filter chips above the list (Listings view only). A status without listings is left out unless it is the
// active filter.
import { html } from "../lib/preact.js";
import { t, fmtNum } from "../i18n.js";
import { useStore, listings, setFilter } from "../state/index.js";

const filters = () => [["all", t("All")], ["new", t("To review")], ["on_hold", t("On hold")], ["approved", t("Approved")],
  ["draft", t("Draft")], ["online", t("Online")], ["sold", t("Sold")]];

export function Filter() {
  const s = useStore();
  let chips = null;
  if (s.data && s.view === "listings") {
    const all = listings();
    chips = filters().map(([k, name]) => {
      const n = k === "all" ? all.length : all.filter((i) => i.status === k).length;
      if (n === 0 && k !== "all" && k !== s.filter) return null;
      return html`<button key=${k} class="chip" aria-pressed=${String(s.filter === k)} data-key=${"filter-" + k}
          onClick=${() => setFilter(k)}>${name}<span class="n">${fmtNum(n)}</span></button>`;
    });
  }
  return html`<nav id="filter" class="filter" aria-label=${t("Filter by status")}>${chips}</nav>`;
}
