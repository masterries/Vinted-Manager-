/* ---------- Line chart: total over all fetches (one line, one axis) ----------
   Props: points [{time: ms, value}] (at least one), m (a metric from metrics.js), width (px),
   active (index of the point under the pointer or null), onHover(event, index), onLeave().
   Everything comes in through props (no store), so the test hook lineChart() can render it on its own.
   The root element is the <svg>. */
import { html } from "../../lib/preact.js";
import { fmtNum, locale } from "../../i18n.js";
import { timeText } from "../../util/format.js";
import { niceScale, textWidth, AXIS_FONT } from "./chartUtils.js";
import { Swatch } from "./metrics.js";

const H = 210, PAD_T = 16, PAD_B = 30, PAD_L = 34, PAD_R = 34;
const DAY = 86400000;

export function LineChart({ points, m, width, active, onHover, onLeave }) {
  const w = Math.max(260, width), innerW = w - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;
  const { max, step } = niceScale(Math.max(...points.map((p) => p.value)));
  const t0 = points[0].time, t1 = points[points.length - 1].time;
  const x = (time) => (points.length === 1 || t1 === t0 ? PAD_L + innerW / 2 : PAD_L + (time - t0) / (t1 - t0) * innerW);
  const y = (v) => PAD_T + innerH - (v / max) * innerH;

  const grid = [];
  for (let v = 0; v <= max; v += step) {
    grid.push(html`<line x1=${PAD_L} x2=${w - PAD_R} y1=${y(v)} y2=${y(v)} stroke=${v === 0 ? "var(--viz-axis)" : "var(--viz-grid)"} stroke-width="1" />`,
      html`<text x=${PAD_L - 7} y=${y(v) + 4} text-anchor="end">${fmtNum(v)}</text>`);
  }

  // Time axis. Fetches close in time sit close on the axis: a label that would overlap the previous one is skipped
  // (the latest fetch is always labelled; earlier labels in its way give way).
  const multiDay = t1 - t0 > 2 * DAY;
  const axisDate = (time) => new Date(time).toLocaleString(locale(), multiDay ? { day: "2-digit", month: "2-digit" }
    : { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  const maxTicks = Math.max(1, Math.min(points.length, Math.floor(innerW / 90)));
  const ticks = points.length === 1 ? [0]
    : [...new Set(Array.from({ length: maxTicks }, (_, k) => Math.round(k * (points.length - 1) / Math.max(1, maxTicks - 1))))];
  const gap = 10, shown = [];
  for (const i of ticks) {
    const label = axisDate(points[i].time), cx = x(points[i].time), lw = textWidth(label, AXIS_FONT);
    const anchor = points.length === 1 ? "middle" : i === 0 ? "start" : i === points.length - 1 ? "end" : "middle";
    const left = anchor === "start" ? cx : anchor === "end" ? cx - lw : cx - lw / 2;
    const tick = { label, cx, anchor, left, right: left + lw };
    const clear = () => !shown.length || shown[shown.length - 1].right + gap <= tick.left;
    if (i === points.length - 1) while (!clear()) shown.pop();
    if (clear()) shown.push(tick);
  }

  let line = null;
  if (points.length > 1) {
    const d = points.map((p, i) => `${i ? "L" : "M"}${x(p.time).toFixed(1)},${y(p.value).toFixed(1)}`).join("");
    line = [html`<path d=${`${d}L${x(t1)},${y(0)}L${x(t0)},${y(0)}Z`} fill=${m.color} fill-opacity="0.1" />`,
      html`<path d=${d} fill="none" stroke=${m.color} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />`];
  }
  const last = points[points.length - 1];

  // Crosshair: snaps to the nearest fetch
  const hot = active !== null && active !== undefined ? points[active] : null;
  const move = (e) => {
    if (!onHover) return;
    const px = e.clientX - e.currentTarget.ownerSVGElement.getBoundingClientRect().left;
    let best = 0;
    points.forEach((p, k) => { if (Math.abs(x(p.time) - px) < Math.abs(x(points[best].time) - px)) best = k; });
    onHover(e, best);
  };

  return html`<svg width=${w} height=${H} role="img" aria-label=${m.total}>
    ${grid}
    ${shown.map((tick) => html`<text x=${tick.cx} y=${H - 9} text-anchor=${tick.anchor}>${tick.label}</text>`)}
    ${line}
    <circle cx=${x(t1)} cy=${y(last.value)} r="4" fill=${m.color} stroke="var(--panel)" stroke-width="2" />
    <text x=${x(t1) + 9} y=${y(last.value) + 4} class="value-label">${fmtNum(last.value)}</text>
    <line x1=${hot ? x(hot.time) : undefined} x2=${hot ? x(hot.time) : undefined} y1=${PAD_T} y2=${PAD_T + innerH}
      stroke="var(--viz-axis)" stroke-width="1" visibility=${hot ? "visible" : "hidden"} />
    <circle cx=${hot ? x(hot.time) : undefined} cy=${hot ? y(hot.value) : undefined} r="4" fill=${m.color} stroke="var(--panel)"
      stroke-width="2" visibility=${hot ? "visible" : "hidden"} />
    <rect x=${PAD_L} y=${PAD_T} width=${innerW} height=${innerH} fill="transparent" onPointerMove=${move} onPointerLeave=${onLeave} />
  </svg>`;
}

// Tooltip content for the point at `index`
export function lineTip(points, m, index) {
  const p = points[index];
  if (!p) return null;
  return html`<div class="row"><${Swatch} color=${m.color} /><b>${fmtNum(p.value)}</b>${m.unit}</div>
    <div class="small">${timeText(new Date(p.time).toISOString())}</div>`;
}
