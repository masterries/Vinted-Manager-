// The list of listings (left column; on phones the first screen). Items are keyed by folder, so the DOM is reused.
import { html } from "../../lib/preact.js";
import { t, fmtNum } from "../../i18n.js";
import { euro, timeText } from "../../util/format.js";
import { imageUrl } from "../../api.js";
import { LOCKED, missingItems } from "../../domain/listing.js";
import { useStore, listings, visibleListings, selectListing } from "../../state/index.js";
import { StatusPill } from "../../components/Badges.js";

const MUTED_PILL = "border-color:transparent;color:var(--muted)";

function item(i, current) {
  const missing = missingItems(i).length;
  const first = (i.photos || [])[0];
  const stats = i.vinted_stats;
  return html`<div key=${i.folder} class="item" aria-current=${String(i.folder === current)} data-folder=${i.folder}
      onClick=${() => selectListing(i.folder, true)}>
    ${first ? html`<img src=${imageUrl(i.folder, first, 360)} alt="" loading="lazy" />` : html`<div class="no-image"></div>`}
    <div style="min-width:0">
      <div class="t">${i.title || i.folder}</div>
      <div class="row">
        <${StatusPill} status=${i.status} />
        ${LOCKED.has(i.status) ? null : (missing
          ? html`<span class="badge-missing">${t("{n} missing", { n: fmtNum(missing) })}</span>`
          : html`<span class="badge-ok">${t("complete")}</span>`)}
        ${stats ? html`<span class="pill" style=${MUTED_PILL} title=${t("As of {time}", { time: timeText(stats.time) })}>
            ${`👁 ${fmtNum(stats.views)} · ♥ ${fmtNum(stats.favorites)}`}</span>` : null}
        ${i.price ? html`<span class="pill" style=${MUTED_PILL}>${euro(i.price)}</span>` : null}
      </div>
    </div>
  </div>`;
}

export function List() {
  const s = useStore();
  if (!s.data || s.view !== "listings") return null;
  const entries = visibleListings();
  if (!entries.length) {
    return html`<div class="empty-list">${listings().length
      ? t("No listings with this status.")
      : t("No items yet. Create a folder with photos for each item in the items folder and let Claude write the listings.")}</div>`;
  }
  return entries.map((i) => item(i, s.current));
}
