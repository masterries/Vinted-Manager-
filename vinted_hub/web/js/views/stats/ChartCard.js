/* ---------- Chart card ----------
   div.chart-card > h3, div.subline, div.chart-area (the chart), div.viz-tip (tooltip), extra children (e.g. <details>).
   - Measures the width of .chart-area and draws the chart only once it is known (before the first paint). Later it
     redraws when the width changed by at least 8 px, 120 ms after the last change (window resize, phone rotation).
   - Hosts the tooltip. The chart reports what the pointer is on: hover.onHover(event, key) / hover.onLeave(), and
     gets hover.active (the key) back to highlight it. The tooltip content is tipContent(key), computed on every
     render, so it follows a language switch or new data while it is shown.
   Props: title, subline, chart(width, hover) -> vnode, tipContent(key) -> children or null, children. */
import { html, useLayoutEffect, useRef, useState } from "../../lib/preact.js";

const MIN_CHANGE = 8;     // px
const DEBOUNCE = 120;     // ms

// Puts the tooltip next to the pointer, inside the card (flips left/up near the right/bottom edge)
export function placeTip(card, tip, clientX, clientY) {
  const r = card.getBoundingClientRect();
  let x = clientX - r.left + 14, y = clientY - r.top + 14;
  if (x + tip.offsetWidth > r.width - 4) x = clientX - r.left - tip.offsetWidth - 14;
  if (y + tip.offsetHeight > r.height - 4) y = clientY - r.top - tip.offsetHeight - 10;
  tip.style.left = Math.max(4, x) + "px";
  tip.style.top = Math.max(4, y) + "px";
}

export function ChartCard({ title, subline, chart, tipContent, children }) {
  const cardRef = useRef(null), areaRef = useRef(null), tipRef = useRef(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [width, setWidth] = useState(0);
  const [tipKey, setTipKey] = useState(null);

  useLayoutEffect(() => {
    const area = areaRef.current;
    let drawn = area.clientWidth, timer = null;
    setWidth(drawn);
    if (typeof ResizeObserver !== "function") return undefined;
    const observer = new ResizeObserver((entries) => {
      const b = Math.round(entries[0].contentRect.width);
      if (Math.abs(b - drawn) < MIN_CHANGE) return;
      drawn = b;
      clearTimeout(timer);
      timer = setTimeout(() => setWidth(area.clientWidth), DEBOUNCE);
    });
    observer.observe(area);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, []);

  const content = tipKey === null ? null : tipContent(tipKey);
  const place = () => { if (tipRef.current && cardRef.current) placeTip(cardRef.current, tipRef.current, pointer.current.x, pointer.current.y); };

  // after every render with a visible tooltip (its size may have changed): place it again
  useLayoutEffect(() => { if (content) place(); });

  const hover = {
    active: content ? tipKey : null,
    onHover: (e, key) => {
      pointer.current = { x: e.clientX, y: e.clientY };
      if (key !== tipKey) setTipKey(key);
      else place();
    },
    onLeave: () => setTipKey(null),
  };

  return html`<div class="chart-card" ref=${cardRef}>
    <h3>${title}</h3>
    <div class="subline">${subline}</div>
    <div class="chart-area" ref=${areaRef}>${width ? chart(width, hover) : null}</div>
    <div class="viz-tip" hidden=${!content} ref=${tipRef}>${content}</div>
    ${children}
  </div>`;
}
