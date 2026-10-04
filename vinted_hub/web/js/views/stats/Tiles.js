// Key figure tile: label (with colour swatch), big number, change since the last fetch, sparkline of the history.
// old === undefined: no previous fetch (history given) or not a history value at all (history null).
import { html } from "../../lib/preact.js";
import { t, fmtNum } from "../../i18n.js";
import { Swatch } from "./metrics.js";
import { Sparkline } from "./Sparkline.js";

function change(diff) {
  if (diff > 0) return t("▲ +{n} since last fetch", { n: fmtNum(diff) });
  if (diff < 0) return t("▼ {n} since last fetch", { n: fmtNum(diff) });
  return t("± 0 since last fetch");
}

export function Tile({ title, value, old, history, color }) {
  const diff = old === undefined ? null : value - old;
  return html`<div class="tile">
    <div class="label">${color ? html`<${Swatch} color=${color} />` : null}${title}</div>
    <div class="value">${fmtNum(value)}</div>
    <div class="bottom">
      ${diff === null ? html`<span>${history ? t("first fetch") : t("currently on Vinted")}</span>`
        : html`<span class=${diff > 0 ? "delta-plus" : null}>${change(diff)}</span>`}
      ${history && history.length > 1 ? html`<${Sparkline} values=${history.slice(-12)} color=${color || "var(--viz-1)"} />` : null}
    </div>
  </div>`;
}
