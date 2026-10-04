/* ---------- Language ----------
   Source strings in the code are English (British spelling); the German translations live in js/i18n/de.<area>.js
   (one dictionary per feature, merged here). Rules:
   - t("Text with {name}", { name }) translates and fills the placeholders. If a value is a vnode (e.g. html`<b>…</b>`),
     t() returns an array of strings and vnodes to use as children; otherwise it returns a string.
   - tn(n, "one …", "many …", vars) picks singular/plural and sets {n} (formatted) unless vars.n is given.
   - Always pass string literals in double quotes to t()/tn(): tools/check_i18n.py reads them from the source.
   - Data values stay English (status, condition, package, brand "No brand"); only their display is translated
     (displayValue). Texts stored in listings (questions, hints, title, description, …) are shown as stored. */
import { remember } from "./lib/storage.js";
import core from "./i18n/de.core.js";
import listings from "./i18n/de.listings.js";
import prices from "./i18n/de.prices.js";
import stats from "./i18n/de.stats.js";

export const LANGUAGES = ["en", "de"];
const DE = Object.assign({}, core, listings, prices, stats);
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const navigatorLanguage = typeof navigator !== "undefined" ? navigator.language || "" : "";

let lang = LANGUAGES.includes(remember("lang")) ? remember("lang") : (/^de\b/i.test(navigatorLanguage) ? "de" : "en");

export const getLanguage = () => lang;
const isVNode = (v) => v !== null && typeof v === "object";   // vnode or array of children

export function t(text, vars) {
  const s = lang === "de" && has(DE, text) ? DE[text] : text;
  if (!vars) return s;
  const parts = s.split(/\{(\w+)\}/);
  const value = (k) => (has(vars, k) && vars[k] !== null && vars[k] !== undefined ? vars[k] : `{${k}}`);
  if (!Object.values(vars).some(isVNode)) return parts.map((p, n) => (n % 2 ? String(value(p)) : p)).join("");
  return parts.map((p, n) => (n % 2 ? value(p) : p)).filter((v) => v !== "").map((v) => (isVNode(v) ? v : String(v)));
}

export function tn(n, one, many, vars) {
  return t(n === 1 ? one : many, Object.assign({ n: fmtNum(n) }, vars));  // i18n-dynamic: both forms are literals at the call
}

export const locale = () => (lang === "de" ? "de-DE" : "en-GB");
export const fmtNum = (v) => Number(v).toLocaleString(locale());
export const langName = (code) => (code === "de" ? t("German") : code === "en" ? t("English") : String(code));

// Writes the language into the document (html lang, tab title). Only call when it really changed (or once at start):
// tests watch the lang attribute and expect exactly one change per switch.
function applyToDocument() {
  document.documentElement.lang = lang;
  document.title = t("Vinted Hub");
}

// Once at start (before the first render).
export function initLanguage() {
  applyToDocument();
}

// Switches the language; returns true if it changed. The caller re-renders (state/settings.js does this via notify()).
export function setLanguage(next) {
  if (!LANGUAGES.includes(next) || next === lang) return false;
  lang = next;
  remember("lang", lang);
  applyToDocument();
  return true;
}

// Data values are English; the UI shows labels in the chosen language.
export function valueLabels(key) {
  if (key === "status") return { new: t("To review"), on_hold: t("On hold"), approved: t("Approved"),
    draft: t("Draft on Vinted"), online: t("Online"), sold: t("Sold") };
  if (key === "condition") return { "New with tags": t("New with tags"), "New without tags": t("New without tags"),
    "Very good": t("Very good"), "Good": t("Good"), "Satisfactory": t("Satisfactory") };
  if (key === "package") return { Small: t("Small"), Medium: t("Medium"), Large: t("Large") };
  if (key === "brand") return { "No brand": t("No brand") };
  return null;
}

// Display text for an English stored value (status, condition, package, brand); other values unchanged
export function displayValue(key, v) {
  const map = valueLabels(key);
  return map && has(map, v) ? map[v] : v;
}
export const statusLabel = (status) => displayValue("status", status);
