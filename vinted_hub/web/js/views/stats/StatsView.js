/* ---------- Statistics view ----------
   Children of <section id="table-view"> (App renders the section): view header with "Fetch statistics", key figure
   tiles, metric switch (views / favourites), two chart cards (total per fetch as a line, current value per listing as
   bars) and the table. Data: state.stats (GET /api/stats, every fetch of the "stats" job is one history entry).
   Plain SVG, one axis per chart, views = --viz-1 blue, favourites = --viz-2 orange (css/stats.css).
   (The test hooks lineChart() and metrics() live in js/test-bridge.js.) */
import { html, useEffect } from "../../lib/preact.js";
import { t, tn, fmtNum } from "../../i18n.js";
import { timeText } from "../../util/format.js";
import { useStore, loadStats, setMetric, startJob, jobRunning } from "../../state/index.js";
import { metrics } from "./metrics.js";
import { ChartCard } from "./ChartCard.js";
import { LineChart, lineTip } from "./LineChart.js";
import { BarChart, barTip } from "./BarChart.js";
import { Tile } from "./Tiles.js";
import { StatsTable } from "./StatsTable.js";

export function StatsView() {
  const s = useStore();
  const stats = s.stats;
  useEffect(() => { if (!stats) loadStats(); });   // never during render; loadStats() shares a running request
  if (!stats) return html`<div class="help">${t("Loading …")}</div>`;

  const history = stats.history || [];
  const chrome = !!s.live.chrome;
  const fetchCount = history.length;
  const header = html`<div class="view-header" key="header">
    <div class="text">${fetchCount
      ? tn(fetchCount, "Last fetch: {time} · {n} fetch saved.", "Last fetch: {time} · {n} fetches saved.", { time: timeText(history[fetchCount - 1].time) }) + " "
      : t("No fetch yet.") + " "}${t("“Fetch statistics” opens your Vinted profile in the Vinted Chrome and reads the views and favourites of all listings (read-only). Every fetch is saved, so you can see the trend.")}</div>
    <button class="btn primary" disabled=${!chrome || jobRunning()} title=${!chrome ? t("Open the Vinted Chrome at the top first") : undefined}
      onClick=${() => startJob("stats")}>${t("Fetch statistics")}</button>
  </div>`;
  if (!history.length) return header;

  const latest = history[history.length - 1].items;
  const previous = history.length > 1 ? Object.fromEntries(history[history.length - 2].items.map((a) => [a.id, a])) : {};
  const firstSeen = {};
  for (const snap of history) for (const a of snap.items) if (!(a.id in firstSeen)) firstSeen[a.id] = snap.time;
  const series = (id) => history.slice(-8).map((snap) => (snap.items.find((a) => a.id === id) || {}).views).filter((v) => v !== undefined);
  const byVintedId = Object.fromEntries((s.data ? s.data.listings : []).filter((i) => i.vinted_id).map((i) => [i.vinted_id, i]));
  const rows = [...latest].sort((a, b) => b.views - a.views || b.favorites - a.favorites);

  // Totals per fetch for the tiles and the line chart
  const totals = history.map((snap) => ({ time: new Date(snap.time).getTime(), iso: snap.time,
    views: snap.items.reduce((sum, a) => sum + (a.views || 0), 0), favorites: snap.items.reduce((sum, a) => sum + (a.favorites || 0), 0) }));
  const now = totals[totals.length - 1], before = totals.length > 1 ? totals[totals.length - 2] : null;
  const online = latest.filter((a) => !a.sold && !a.draft).length;
  const allMetrics = metrics();
  const metric = s.metric in allMetrics ? s.metric : "views";
  const m = allMetrics[metric];
  const points = totals.map((p) => ({ time: p.time, value: p[metric] }));
  const barRows = [...latest].sort((a, b) => b[metric] - a[metric] || b.views - a.views);

  return [
    header,
    html`<div class="tiles" key="tiles">
      <${Tile} title=${t("Total views")} value=${now.views} old=${before ? before.views : undefined} history=${totals.map((p) => p.views)} color="var(--viz-1)" />
      <${Tile} title=${t("Total favourites")} value=${now.favorites} old=${before ? before.favorites : undefined} history=${totals.map((p) => p.favorites)} color="var(--viz-2)" />
      <${Tile} title=${t("Listings online")} value=${online} old=${undefined} history=${null} color=${null} />
    </div>`,
    html`<div class="metric-row" key="metric">${t("Charts show:")}<div class="segmented">${Object.entries(allMetrics).map(([k, v]) =>
      html`<button key=${k} aria-pressed=${String(metric === k)} data-key=${"metric-" + k} onClick=${() => setMetric(k)}>${v.name}</button>`)}</div></div>`,
    html`<div class="charts" key="charts">
      <${ChartCard} title=${m.total}
        subline=${totals.length > 1 ? t("{n} fetches since {time}", { n: fmtNum(totals.length), time: timeText(totals[0].iso) })
          : t("Only one fetch so far – from the second fetch on, a line appears here.")}
        chart=${(width, hover) => html`<${LineChart} points=${points} m=${m} width=${width} ...${hover} />`}
        tipContent=${(index) => lineTip(points, m, index)}>
        <details><summary style="cursor:pointer">${t("Values as a table")}</summary>
          <table><tr><th>${t("Fetch")}</th><th>${t("Views")}</th><th>${t("Favourites")}</th></tr>
            ${[...totals].reverse().map((p) => html`<tr key=${p.iso}><td>${timeText(p.iso)}</td><td>${fmtNum(p.views)}</td><td>${fmtNum(p.favorites)}</td></tr>`)}
          </table>
        </details>
      </${ChartCard}>
      <${ChartCard} title=${m.perListing}
        subline=${t("As of {time} · all values also in the table below", { time: timeText(now.iso) })}
        chart=${(width, hover) => html`<${BarChart} rows=${barRows} m=${m} metricKey=${metric} width=${width} ...${hover} />`}
        tipContent=${(id) => barTip(barRows, m, metric, previous, id)} />
    </div>`,
    html`<${StatsTable} key="table" rows=${rows} previous=${previous} byVintedId=${byVintedId} series=${series} firstSeen=${firstSeen} />`,
  ];
}
