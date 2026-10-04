// Rules about a listing that several parts of the page share (no state, no DOM): what is missing, tips, field names.
import { t } from "../i18n.js";
import { num, euro } from "../util/format.js";

export const LOCKED = new Set(["draft", "online", "sold"]);            // already on Vinted: fields read-only
export const NOT_ON_VINTED = new Set(["new", "on_hold", "approved"]);
export const EMPTY = /^\s*(unbekannt|unklar|unknown|unclear|n\/?a|tbd|-|\?|\[\?[^\]]*\])?\s*$/i;
export const PLACEHOLDER = /\[\?/;

export const openQuestions = (i) => (i.questions || []).filter((q) => !q.answer);

export const required = () => [["title", t("Title")], ["description", t("Description")], ["category", t("Category")],
  ["brand", t("Brand (or “No brand”)")], ["size", t("Size")], ["condition", t("Condition")], ["package", t("Package size")]];
export const textChecks = () => [["title", t("Title")], ["description", t("Description")], ["category", t("Category")], ["brand", t("Brand")],
  ["size", t("Size")], ["color", t("Colour")], ["material", t("Material")], ["shape", t("Shoe shape")], ["heel_height", t("Heel height")]];

// Field name in the UI language (JSON key -> label); unknown keys unchanged
export function fieldName(key) {
  const names = Object.fromEntries([...textChecks(), ["condition", t("Condition")], ["package", t("Package size")], ["price", t("Price")],
    ["min_price", t("Minimum price")], ["notes", t("Note")], ["photos", t("Photos")], ["status", t("Status")]]);
  return Object.prototype.hasOwnProperty.call(names, key) ? names[key] : key;
}

// What blocks approval: [{field|null, text} | {field|null, question}] (open questions first, in their order)
export function missingItems(i) {
  const f = [];
  const questions = openQuestions(i);
  const perQuestion = new Set(questions.map((q) => q.field).filter(Boolean));
  if (i._folder_missing) f.push({ field: null, text: t("Photo folder no longer exists") });
  for (const q of questions) f.push({ field: q.field || null, question: q });
  if (!(i.photos || []).length) f.push({ field: "photos", text: t("Select at least one photo") });
  for (const [k, name] of required()) if (!perQuestion.has(k) && EMPTY.test(i[k] ?? "")) f.push({ field: k, text: t("{name} is missing", { name }) });
  // Placeholders without an open question must be removed by hand
  if (!questions.length) for (const [k, name] of textChecks())
    if (!EMPTY.test(i[k] ?? "") && PLACEHOLDER.test(i[k] || "")) f.push({ field: k, text: t("{name}: replace or delete the placeholder [? …]", { name }) });
  const price = num(i.price);
  if (String(i.price ?? "").trim() && !Number.isFinite(price)) f.push({ field: "price", text: t("Price is not a valid number") });
  else if (!(price > 0)) f.push({ field: "price", text: t("Price is missing") });
  return f;
}

// Non-blocking hints shown under "Still missing"
export function tips(i) {
  const out = [];
  const n = (i.photos || []).length;
  if (n > 0 && n < 3) out.push(t("Fewer than 3 photos: buyers want to see the side, the sole and the size label."));
  if (n > 20) out.push(t("Vinted takes at most 20 photos; the last {n} will be left out when uploading.", { n: n - 20 }));
  if ((i._missing_photos || []).length) out.push(t("No longer in the folder: {files}", { files: i._missing_photos.join(", ") }));
  if (EMPTY.test(i.color ?? "")) out.push(t("Colour is empty (optional, but it helps buyers find the item)."));
  if ((i.title || "").length > 60) out.push(t("The title is long: put the key facts (brand, type, size) first."));
  if (num(i.min_price) > 0 && num(i.price) > 0 && num(i.min_price) > num(i.price)) out.push(t("The minimum price is higher than the price."));
  const vp = i.vinted_price;
  if (vp && vp.premium && num(i.price) > vp.premium * 1.3)
    out.push(t("Your price is well above Vinted’s suggestion (optimal {optimal}, premium {premium}). That can slow down the sale.",
      { optimal: euro(vp.optimal), premium: euro(vp.premium) }));
  return out;
}

// All photos in lightbox order: the chosen ones (cover first), then the unused ones of the folder
export const photoOrder = (i) => [...(i.photos || []), ...(i._all_photos || []).filter((f) => !(i.photos || []).includes(f))];

// Listings not yet on Vinted whose text is in another language than the setting (missing field = "en")
export function languageMismatch(listings, settings) {
  const result = { title: 0, description: 0 };
  for (const i of listings || []) {
    if (!NOT_ON_VINTED.has(i.status)) continue;
    for (const key of ["title", "description"])
      if (String(i[key] || "").trim() && (i[key + "_language"] || "en") !== settings[key + "_language"]) result[key]++;
  }
  return result;
}
