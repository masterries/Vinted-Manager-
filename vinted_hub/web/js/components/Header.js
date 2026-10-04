// Page header: name, view switch, counts, Vinted Chrome status, Reload, Settings, and the status filter (own row).
// View switch and counts appear once the data is loaded. The header's height is published as --header-h on <html>
// (the sticky list below uses it).
import { html, useLayoutEffect, useRef } from "../lib/preact.js";
import { t, tn, fmtNum } from "../i18n.js";
import { num, euro } from "../util/format.js";
import { LOCKED } from "../domain/listing.js";
import { useStore, listings, showView, reload, openSettings } from "../state/index.js";
import { ChromeStatus } from "./ChromeStatus.js";
import { Filter } from "./Filter.js";
import { GearIcon } from "./icons.js";

const views = () => [["listings", t("Listings")], ["prices", t("Prices")], ["stats", t("Statistics")]];

// "12 pairs · 3 to review · …" with the numbers in bold
function headerStats() {
  const all = listings();
  const count = (statuses) => all.filter((i) => statuses.includes(i.status)).length;
  const sold = all.filter((i) => i.status === "sold");
  const revenue = sold.reduce((sum, i) => sum + (num(i.price) || 0), 0);
  const withoutPrice = all.filter((i) => !LOCKED.has(i.status) && !(num(i.price) > 0)).length;
  const pairs = all.length;
  const b = (n) => html`<b>${fmtNum(n)}</b>`;
  const parts = [
    tn(pairs, "{n} pair", "{n} pairs", { n: b(pairs) }),
    t("{n} to review", { n: b(count(["new", "on_hold"])) }),
    t("{n} approved", { n: b(count(["approved"])) }),
    t("{n} on Vinted", { n: b(count(["draft", "online"])) }),
    t("{n} sold ({revenue})", { n: b(sold.length), revenue: euro(revenue) }),
    withoutPrice ? t("{n} without a price", { n: b(withoutPrice) }) : null].filter(Boolean);
  return parts.flatMap((p, k) => (k ? [" · ", p] : [p]));
}

export function Header() {
  const s = useStore();
  const ref = useRef(null);
  useLayoutEffect(() => {
    const header = ref.current;
    const publish = () => document.documentElement.style.setProperty("--header-h", header.offsetHeight + "px");
    const observer = new ResizeObserver(publish);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
  const loaded = !!s.data;
  return html`<header class="header" ref=${ref}>
    <h1 id="app-name">${t("Vinted Hub")}</h1>
    <nav id="view-switch" class="segmented" aria-label=${t("View")}>${loaded ? views().map(([k, name]) =>
      html`<button key=${k} aria-pressed=${String(s.view === k)} data-key=${"view-" + k} onClick=${() => showView(k)}>${name}</button>`) : null}</nav>
    <div id="header-stats" class="header-stats">${loaded ? headerStats() : null}</div>
    <div class="header-right">
      <${ChromeStatus} />
      <button id="reload" class="btn" type="button" title=${t("Re-read listings.json and the photo folders")} onClick=${reload}>${t("Reload")}</button>
      <button id="settings-button" class="btn settings-button" type="button" aria-haspopup="dialog"
          title=${t("Settings")} aria-label=${t("Settings")} onClick=${openSettings}>
        <${GearIcon} /><span class="label-text">${t("Settings")}</span>
      </button>
    </div>
    <${Filter} />
  </header>`;
}
