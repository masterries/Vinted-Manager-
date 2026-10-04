/* ---------- Test bridge ----------
   The browser regression tests (and anyone debugging in the console) use the names of the old single-file page:
   D, STATS, LIVE, SETTINGS, CHOICES, SETTINGS_INFO, CONFLICTS, current, filter, metric, load(), pollStatus(),
   selectListing(), showView(), showSaveState(), changeSetting(), renderAll()/renderDetail()/renderStats(), locale(),
   lineChart(), metrics(). They map onto the store and the chart components here, so no view carries test code.
   Tests may change objects in place (D.listings = …, CONFLICTS[x] = …) and then call a render function, which simply
   re-renders. App code never uses these globals. */
import { html, render, useState } from "./lib/preact.js";
import { exposeFunctions, exposeState } from "./lib/testHooks.js";
import { locale } from "./i18n.js";
import {
  state, notify, load, pollStatus, selectListing, showView, showSaveState, changeSetting,
} from "./state/index.js";
import { metrics } from "./views/stats/metrics.js";
import { placeTip } from "./views/stats/ChartCard.js";
import { LineChart, lineTip } from "./views/stats/LineChart.js";

exposeState("D", () => state.data);
exposeState("STATS", () => state.stats);
exposeState("LIVE", () => state.live);
exposeState("SETTINGS", () => state.settings);
exposeState("CHOICES", () => state.choices);
exposeState("SETTINGS_INFO", () => state.settingsInfo);
exposeState("CONFLICTS", () => state.conflicts);
exposeState("current", () => state.current);
// plain assignments in tests (`filter = 'sold'`) set the value without remembering it; a render call follows
exposeState("filter", () => state.filter, (v) => { state.filter = v; });
exposeState("metric", () => state.metric, (v) => { state.metric = v; });

/* lineChart(card, tip, points, m, width): a detached <svg> of the line chart, rendered on its own (the old page's
   lineChart()). The crosshair works; the tooltip goes into `tip`, placed inside `card`. */
function StandaloneLineChart({ card, tip, points, m, width }) {
  const [active, setActive] = useState(null);
  const onHover = (e, index) => {
    setActive(index);
    if (!card || !tip) return;
    render(lineTip(points, m, index), tip);
    tip.hidden = false;
    placeTip(card, tip, e.clientX, e.clientY);
  };
  const onLeave = () => { setActive(null); if (tip) tip.hidden = true; };
  return html`<${LineChart} points=${points} m=${m} width=${width} active=${active} onHover=${onHover} onLeave=${onLeave} />`;
}

function lineChart(card, tip, points, m, width) {
  const host = document.createElement("div");
  render(html`<${StandaloneLineChart} card=${card} tip=${tip} points=${points} m=${m} width=${width} />`, host);
  return host.firstElementChild;
}

const rerender = () => notify();
exposeFunctions({
  load, pollStatus, selectListing, showView, showSaveState, changeSetting, locale,
  renderAll: rerender, renderDetail: rerender, renderStats: rerender,
  lineChart, metrics,
});
