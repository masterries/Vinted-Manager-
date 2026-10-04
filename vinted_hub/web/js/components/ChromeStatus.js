// Header: is the Vinted Chrome open? Plus "Fill in all approved" / "Fetch statistics" (Chrome open, no job running)
// and "Open" (Chrome closed). Empty until the data or a status poll arrived (the server may be unreachable).
import { html } from "../lib/preact.js";
import { t, fmtNum } from "../i18n.js";
import { useStore, listings, jobRunning, startJob, openChrome } from "../state/index.js";

export function ChromeStatus() {
  const s = useStore();
  const known = !!(s.data || s.live.job);
  const chrome = !!s.live.chrome;
  const all = listings();
  const approved = all.filter((i) => i.status === "approved").length;
  const atVinted = all.filter((i) => i.status === "online" || i.status === "draft").length;
  const running = jobRunning();
  return html`<span id="chrome-status" class=${chrome ? "chrome-status on" : "chrome-status"}>${known ? [
    chrome && approved && !running
      ? html`<button class="btn small" style="margin-right:6px" data-key="chrome-fill"
          title=${t("Fills in the approved listings one after another in the Vinted Chrome. After each one it waits until you have submitted it yourself.")}
          onClick=${() => startJob("fill_approved")}>${t("Fill in all approved ({n})", { n: fmtNum(approved) })}</button>`
      : null,
    chrome && atVinted && !running
      ? html`<button class="btn small" style="margin-right:6px" data-key="chrome-stats"
          title=${t("Reads the views and favourites of all your Vinted listings and saves them in the history (read-only).")}
          onClick=${() => startJob("stats")}>${t("Fetch statistics")}</button>`
      : null,
    html`<span class="dot"></span>`,
    chrome ? t("Vinted Chrome open") : t("Vinted Chrome closed"),
    chrome ? null : html`<button class="btn small" data-key="chrome-open" onClick=${openChrome}>${t("Open")}</button>`,
  ] : null}</span>`;
}
