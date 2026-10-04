// Panel of the job running in the Vinted Chrome (fill, fill_approved, prices, stats): title, log, Cancel / Close.
// Shown while a job runs and after it ended (until "Close"); empty and hidden otherwise.
// The job title and log come from the server, already in the UI language.
// Cancel and Close share one slot; they are keyed by their data-key, so a focused Cancel is replaced (not turned into
// Close) when the job ends, and focus falls back to the page.
import { html, useLayoutEffect, useRef } from "../lib/preact.js";
import { t } from "../i18n.js";
import { useStore, byFolder, stopJob, dismissJob } from "../state/index.js";

export function JobPanel() {
  const s = useStore();
  const pre = useRef(null);
  const shownJob = useRef(null);
  const j = s.live.job;
  const hidden = !j || (!j.running && (j.exit_code === null || s.jobDismissed)) || !j.title;

  // Scroll the log to its end whenever a changed job status arrived (the poll keeps the old object when nothing
  // changed) - not on unrelated re-renders
  useLayoutEffect(() => {
    if (hidden) { shownJob.current = null; return; }
    if (pre.current && shownJob.current !== j) pre.current.scrollTop = pre.current.scrollHeight;
    shownJob.current = j;
  });

  if (hidden) return html`<div id="job" class="job" hidden></div>`;
  const i = j.folder ? byFolder(j.folder) : null;
  return html`<div id="job" class="job">
    <h3>${j.running ? "⏳" : (j.exit_code === 0 ? "✓" : "⚠")}${j.title}</h3>
    ${i ? html`<div class="help" style="margin-bottom:6px;font-size:13px">${i.title}</div>` : null}
    ${j.running ? html`<div style="font-size:13px;margin-bottom:6px">
        ${t("Running in the Vinted Chrome. Check the form there and click “Save draft” or “Upload” yourself.")}</div>` : null}
    <pre ref=${pre}>${(j.log || []).slice(-12).join("\n") || "…"}</pre>
    <div class="tools" style="margin-top:0">
      ${j.running
        ? html`<button key="job-stop" class="btn small" data-key="job-stop" onClick=${stopJob}>${t("Cancel")}</button>`
        : html`<button key="job-close" class="btn small" data-key="job-close" onClick=${dismissJob}>${t("Close")}</button>`}
    </div>
  </div>`;
}
