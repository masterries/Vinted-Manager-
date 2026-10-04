// Statistics table: every item of the latest fetch with status, price, views/favourites (+ change), views history,
// first seen. Items that belong to a hub listing (vinted_id) get its cover photo and an "open in the hub" link.
import { html } from "../../lib/preact.js";
import { t, tn, fmtNum } from "../../i18n.js";
import { euro, timeText, webUrl } from "../../util/format.js";
import { imageUrl } from "../../api.js";
import { showView } from "../../state/index.js";
import { Delta } from "../../components/Badges.js";
import { Sparkline } from "./Sparkline.js";

// Status of an item on Vinted (from the stats fetch, not the hub status)
export const vintedStatus = (a) => (a.sold ? t("Sold") : a.reserved ? t("Reserved") : a.draft ? t("Draft") : a.hidden ? t("Hidden") : t("Online"));

// rows: latest items sorted; previous: items of the fetch before, by id; byVintedId: hub listings by vinted_id;
// series(id): views of the last fetches; firstSeen: id -> time of the first fetch that had the item
export function StatsTable({ rows, previous, byVintedId, series, firstSeen }) {
  const total = (k) => rows.reduce((sum, a) => sum + (a[k] || 0), 0);
  const head = ["", t("Listing"), t("Status"), t("Price"), t("Views"), t("Favourites"), t("Views history"), t("First seen")];
  return html`<div class="table-frame"><table class="table">
    <thead><tr>${head.map((label) => html`<th>${label}</th>`)}</tr></thead>
    <tbody>${rows.map((a) => {
      const i = byVintedId[a.id];
      const old = previous[a.id] || {};
      const views = series(a.id);
      const cover = i && (i.photos || [])[0];
      return html`<tr key=${a.id}>
        <td>${cover ? html`<img src=${imageUrl(i.folder, cover, 360)} alt="" loading="lazy" />` : null}</td>
        <td><a class="title-link" href=${webUrl(a.url)} target="_blank" rel="noopener" style="color:inherit">${a.title}</a>${i
          ? html`<div class="small"><span class="title-link" onClick=${() => showView("listings", i.folder)}>${t("open in the hub")}</span></div>`
          : html`<div class="small">${t("not in the hub")}</div>`}</td>
        <td>${vintedStatus(a)}</td>
        <td style="white-space:nowrap">${euro(a.price)}</td>
        <td style="white-space:nowrap"><b>${fmtNum(a.views)}</b><${Delta} now=${a.views} old=${old.views} /></td>
        <td style="white-space:nowrap"><b>${fmtNum(a.favorites)}</b><${Delta} now=${a.favorites} old=${old.favorites} /></td>
        <td title=${views.map(fmtNum).join(" → ")}><${Sparkline} values=${views} color="var(--viz-1)" /></td>
        <td class="small" style="white-space:nowrap">${timeText(firstSeen[a.id])}</td>
      </tr>`;
    })}</tbody>
    <tfoot><tr><td></td><td>${tn(rows.length, "{n} item on Vinted", "{n} items on Vinted")}</td><td></td><td></td>
      <td>${fmtNum(total("views"))}</td><td>${fmtNum(total("favorites"))}</td><td></td><td></td></tr></tfoot>
  </table></div>`;
}
