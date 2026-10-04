// Small shared display pieces used by several views.
import { html } from "../lib/preact.js";
import { statusLabel } from "../i18n.js";
import { fmtNum } from "../util/format.js";

// Status pill (colour from the s-<status> class). Extra props (style, title) go to the span.
export function StatusPill({ status, ...rest }) {
  return html`<span class=${`pill s-${status}`} ...${rest}>${statusLabel(status)}</span>`;
}

// "+3" / "-1" change badge next to a number; nothing when unchanged or no previous value
export function Delta({ now, old }) {
  if (old === undefined || old === null || now === old) return null;
  return html`<span class=${now > old ? "badge-ok" : "badge-missing"} style="margin-left:6px">${`${now > old ? "+" : ""}${fmtNum(now - old)}`}</span>`;
}
