// div#actions: the bar at the bottom with what to do next for the selected listing (depends on its status).
// [hidden] when no listing is selected (as before; note that .actions {display: flex} wins over [hidden]);
// content only in the Listings view (body.table-mode hides the bar in the other views).
// Every button is keyed by the listing and its data-key: when a status change or a listing switch gives the slot
// another action (or the same action for another listing), Preact builds a new button instead of reusing the
// focused one, so focus falls back to the page (as before) and a second Enter or a key repeat does nothing.
import { html } from "../../lib/preact.js";
import { t, tn } from "../../i18n.js";
import { timeText, webUrl } from "../../util/format.js";
import { missingItems } from "../../domain/listing.js";
import { useStore, currentListing, jobRunning, setStatus, startJob, preparePhotos } from "../../state/index.js";
import { Delta } from "../../components/Badges.js";

// Preact key of a button: the listing + the button's data-key
const keyOf = (i, dataKey) => `${i.folder}|${dataKey}`;

function statusButton(i, text, status, primary, extra) {
  return html`<button key=${keyOf(i, "status-" + status)} class=${"btn" + (primary ? " primary" : "")} data-key=${"status-" + status} ...${extra || {}}
      onClick=${() => setStatus(status)}>${text}</button>`;
}

// The link comes from the data (vinted_url): only an http(s) address becomes a link (never "javascript:" etc.)
function vintedLink(url) {
  const href = webUrl(url);
  return href ? html`<div class="tools"><a class="btn small" href=${href} target="_blank" rel="noopener" style="text-decoration:none">${t("View on Vinted ↗")}</a></div>` : null;
}

function parts(i, s) {
  const missingCount = missingItems(i).length;
  if (i.status === "new" || i.status === "on_hold") {
    return [
      html`<div class="text">${missingCount
        ? tn(missingCount, "{n} detail still missing, see above.", "{n} details still missing, see above.")
        : t("Ready. After approval the listing can be uploaded.")}</div>`,
      i.status === "new" ? statusButton(i, t("Put on hold"), "on_hold") : statusButton(i, t("Review again"), "new"),
      statusButton(i, t("Approve ✓"), "approved", true, { disabled: missingCount > 0, title: missingCount ? t("Fill in the missing details first") : undefined }),
    ];
  }
  if (i.status === "approved") {
    const running = jobRunning();
    const chrome = !!s.live.chrome;
    return [
      html`<div class="text">${t("Approved. “Fill in on Vinted” fills in the form in the Vinted Chrome; you submit it there yourself.")}
        <div class="tools">
          <button key=${keyOf(i, "prepare-photos")} class="btn small" data-key="prepare-photos" onClick=${preparePhotos}>${t("By hand: prepare photos")}</button>
          <a class="btn small" href=${webUrl(s.data.domain) ? s.data.domain + "/items/new" : undefined} target="_blank" rel="noopener" style="text-decoration:none">${t("Open the Vinted form ↗")}</a>
        </div>
      </div>`,
      statusButton(i, t("Withdraw approval"), "new"),
      html`<button key=${keyOf(i, "fill-one")} class="btn primary" disabled=${running || !chrome} data-key="fill-one"
          title=${!chrome ? t("Open the Vinted Chrome at the top first") : (running ? t("A job is already running") : undefined)}
          onClick=${() => startJob("fill", i.folder)}>${t("Fill in on Vinted")}</button>`,
    ];
  }
  if (i.status === "draft") {
    return [
      html`<div class="text">${t("Created on Vinted (as a draft or already uploaded). Check it there, then set the status here.")}${vintedLink(i.vinted_url)}</div>`,
      statusButton(i, t("Back to approved"), "approved"),
      statusButton(i, t("Is online ✓"), "online", true),
    ];
  }
  if (i.status === "online") {
    const st = i.vinted_stats;
    const views = st ? Number(st.views) || 0 : 0, favorites = st ? Number(st.favorites) || 0 : 0;
    return [
      html`<div class="text">${t("Online on Vinted.")}${st
        ? [" ", html`<b>${tn(views, "{n} view", "{n} views")}</b>`, html`<${Delta} now=${st.views} old=${st.views_before} />`, " · ",
           html`<b>${tn(favorites, "{n} favourite", "{n} favourites")}</b>`, html`<${Delta} now=${st.favorites} old=${st.favorites_before} />`,
           " ", t("(as of {time})", { time: timeText(st.time) })]
        : " " + t("No statistics fetched yet.")}${vintedLink(i.vinted_url)}</div>`,
      statusButton(i, t("Back to approved"), "approved"),
      statusButton(i, t("Sold ✓"), "sold", true),
    ];
  }
  if (i.status === "sold") {
    return [
      html`<div class="text">${t("Sold 🎉")}</div>`,
      statusButton(i, t("Not sold after all"), "online"),
    ];
  }
  return [];
}

export function ActionsBar() {
  const s = useStore();
  const i = currentListing();
  return html`<div id="actions" class="actions" hidden=${!i}>${i && s.view === "listings" ? parts(i, s) : null}</div>`;
}
