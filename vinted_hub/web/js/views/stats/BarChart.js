/* ---------- Bar chart: current value per listing as horizontal bars (one colour, sorted by the caller) ----------
   Props: rows (items of the latest fetch), m (metric), metricKey ("views" | "favorites"), width (px),
   active (id of the row under the pointer or null), onHover(event, id), onLeave(). Rows are 28 px high. */
import { html } from "../../lib/preact.js";
import { t, fmtNum } from "../../i18n.js";
import { euro } from "../../util/format.js";
import { niceScale, truncate } from "./chartUtils.js";
import { Swatch } from "./metrics.js";

const ROW_H = 28, THICK = 14, PAD_T = 4, PAD_B = 24, PAD_R = 34, RADIUS = 4;

export function BarChart({ rows, m, metricKey: key, width, active, onHover, onLeave }) {
  const w = Math.max(260, width), labelW = Math.min(240, Math.round(w * 0.42));
  const innerW = w - labelW - PAD_R, H = PAD_T + rows.length * ROW_H + PAD_B;
  const { max, step } = niceScale(Math.max(...rows.map((a) => a[key])));
  const x = (v) => labelW + (v / max) * innerW;

  const grid = [];
  for (let v = 0; v <= max; v += step) {
    grid.push(html`<line x1=${x(v)} x2=${x(v)} y1=${PAD_T} y2=${H - PAD_B} stroke=${v === 0 ? "var(--viz-axis)" : "var(--viz-grid)"} stroke-width="1" />`,
      html`<text x=${x(v)} y=${H - 8} text-anchor="middle">${fmtNum(v)}</text>`);
  }

  const bars = rows.map((a, n) => {
    const yMid = PAD_T + n * ROW_H + ROW_H / 2, y0 = yMid - THICK / 2, bw = x(a[key]) - labelW, r = RADIUS;
    let bar = null;
    if (bw >= r) {
      bar = html`<path class="bar" fill=${m.color}
        d=${`M${labelW},${y0}h${bw - r}a${r},${r} 0 0 1 ${r},${r}v${THICK - 2 * r}a${r},${r} 0 0 1 ${-r},${r}h${-(bw - r)}Z`} />`;
    } else if (bw > 0) {
      bar = html`<rect class="bar" x=${labelW} y=${y0} width=${bw} height=${THICK} fill=${m.color} />`;
    }
    return html`<g key=${a.id} class=${active === a.id ? "row-active" : null}>
      <text x=${labelW - 8} y=${yMid + 4} text-anchor="end" class="bar-label">${truncate(String(a.title ?? ""), labelW - 14)}</text>
      ${bar}
      <text x=${x(a[key]) + 6} y=${yMid + 4} class="value-label">${fmtNum(a[key])}</text>
      <rect x="0" y=${yMid - ROW_H / 2} width=${w} height=${ROW_H} fill="transparent"
        onPointerMove=${(e) => onHover && onHover(e, a.id)} onPointerLeave=${onLeave} />
    </g>`;
  });

  return html`<svg width=${w} height=${H} role="img" aria-label=${m.perListing}>${grid}${bars}</svg>`;
}

// Tooltip content for the row with `id`; previous: items of the fetch before, by id (for the change)
export function barTip(rows, m, key, previous, id) {
  const a = rows.find((row) => row.id === id);
  if (!a) return null;
  const old = previous[a.id];
  const diff = old ? a[key] - old[key] : 0;
  const change = diff ? " " + t("({change} since last fetch)", { change: `${diff > 0 ? "+" : ""}${fmtNum(diff)}` }) : "";
  return html`<div class="row"><${Swatch} color=${m.color} /><b>${fmtNum(a[key])}</b>${m.unit + change}</div>
    <div>${a.title}</div>
    <div class="small">${t("{views} views · {favourites} favourites · {price}", { views: fmtNum(a.views), favourites: fmtNum(a.favorites), price: euro(a.price) })}</div>`;
}
