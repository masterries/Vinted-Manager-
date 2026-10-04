// Tiny trend line (84 × 22 px) for the tiles and the table: grey line, last value as a coloured dot.
// Fewer than two values: a short text instead.
import { html } from "../../lib/preact.js";
import { t, fmtNum } from "../../i18n.js";

const W = 84, H = 22;

export function Sparkline({ values, color }) {
  if (values.length < 2) return html`<span class="small">${values.length ? t("only 1 fetch") : "–"}</span>`;
  const max = Math.max(1, ...values);
  const pt = values.map((v, i) => [2 + i * (W - 8) / (values.length - 1), H - 4 - (v / max) * (H - 8)]);
  const last = pt[pt.length - 1];
  return html`<svg width=${W} height=${H} role="img" aria-label=${t("History: {values}", { values: values.map(fmtNum).join(", ") })}>
    <path d=${pt.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("")} fill="none"
      stroke="var(--viz-muted)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
    <circle cx=${last[0]} cy=${last[1]} r="3" fill=${color} stroke="var(--panel)" stroke-width="1.5" />
  </svg>`;
}
