// Numbers, money, dates - all formatted for the current UI language (en-GB / de-DE) - and safe link targets.
import { getLanguage, locale, fmtNum } from "../i18n.js";

export { fmtNum };

// "12,50 €" / "12.5" / "12,-" -> 12.5 (NaN if not a number; "" -> 0)
export const num = (v) => Number(String(v ?? "").replace(/[€\s]/g, "").replace(/[.,]-$/, "").replace(",", "."));

export const clone = (x) => JSON.parse(JSON.stringify(x ?? null));

// Link target built from data (vinted_url, stats item url, the configured domain): only an http(s) address, otherwise
// undefined (no href), so a "javascript:" or other value can never become a clickable link in the hub's origin.
export const webUrl = (url) => (/^https?:\/\//i.test(String(url || "")) ? String(url) : undefined);

// Decimal comma in German input fields
export const decimalText = (v) => (getLanguage() === "de" ? String(v).replace(".", ",") : String(v));

export function euro(v) {
  if (v === null || v === undefined || v === "") return "–";
  const n = num(v);
  if (!Number.isFinite(n)) return `${v} €`;
  return new Intl.NumberFormat(locale(), { style: "currency", currency: "EUR",
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2, maximumFractionDigits: 2 }).format(n);
}

// ISO time -> "03/10, 14:05" (day, month, hour, minute); empty -> "–"
export const timeText = (iso) => (iso ? new Date(iso).toLocaleString(locale(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "–");

// "2026-09-30" or ISO -> "30/09/2026"; unparseable text is returned unchanged
export function dateText(text) {
  const d = /^\d{4}-\d{2}-\d{2}$/.test(String(text)) ? new Date(text + "T00:00:00") : new Date(text);
  return isNaN(d) ? String(text) : d.toLocaleDateString(locale(), { day: "2-digit", month: "2-digit", year: "numeric" });
}
