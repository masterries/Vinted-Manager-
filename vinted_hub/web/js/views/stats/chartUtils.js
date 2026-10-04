// Small helpers for the plain-SVG charts (no chart library): axis scale and text measuring.

// "Nice" axis maximum and step for values up to `max` (about 4 grid lines, steps 1/2/5/10 × 10^n, at least 1)
export function niceScale(max) {
  if (!(max > 0)) return { max: 4, step: 1 };
  const raw = max / 4, p = 10 ** Math.floor(Math.log10(raw)), f = raw / p;
  const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p);
  return { max: Math.ceil(max / step) * step, step };
}

// Same font as ".chart-area svg text" in css/stats.css (axis labels)
export const AXIS_FONT = '11px system-ui, -apple-system, "Segoe UI", sans-serif';
const LABEL_FONT = '12px system-ui, -apple-system, "Segoe UI", sans-serif';   // ".bar-label"

let measurer = null;
// Width of `text` in pixels when drawn in `font` (measured on a canvas that is never shown)
export function textWidth(text, font) {
  measurer = measurer || document.createElement("canvas").getContext("2d");
  measurer.font = font;
  return measurer.measureText(text).width;
}

function measureCut(text, width) {
  if (textWidth(text, LABEL_FONT) <= width) return text;
  let out = text;
  while (out.length > 1 && textWidth(out + "…", LABEL_FONT) > width) out = out.slice(0, -1);
  return out + "…";
}

// Shortens a bar label with "…" so that it fits into `width` pixels. Results are cached (one canvas measurement per
// removed character is too slow to repeat for every bar on every render, e.g. on each hover change); the cache is
// emptied when it grows past CUT_LIMIT entries (titles × widths seen since).
const CUT_LIMIT = 500;
const cut = new Map();
export function truncate(text, width) {
  const key = width + "|" + text;   // width is a number, so the first "|" ends it
  let out = cut.get(key);
  if (out === undefined) {
    if (cut.size >= CUT_LIMIT) cut.clear();
    out = measureCut(text, width);
    cut.set(key, out);
  }
  return out;
}
