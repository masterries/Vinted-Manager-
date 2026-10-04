// The "Listing" card: all text fields, choices, prices and the note of the selected listing.
// Fields keep their DOM nodes across re-renders (fixed order, components/inputs.js), so typing, focus and caret survive
// the status poll and a language switch. Edits go to the store at once (editField) and are saved after a short pause;
// leaving a field (blur/change) saves immediately.
import { html } from "../../lib/preact.js";
import { t, tn, displayValue, langName } from "../../i18n.js";
import { euro, dateText, decimalText } from "../../util/format.js";
import { LOCKED } from "../../domain/listing.js";
import { editField, saveNow, copyText } from "../../state/index.js";
import { TextInput, TextArea } from "../../components/inputs.js";
import { PriceChoices } from "../../components/PriceChoices.js";

const charCount = (n) => tn(n, "{n} character", "{n} characters");
const saveSoon = () => saveNow().catch(() => {});

// One field: label (+ language badge, counter, Copy), the input, optional help below.
// opt: {wide, long, number, choices, placeholder, help, counter, badge, copy, locked}
function field(i, key, label, opt, missing) {
  const raw = i[key] === null || i[key] === undefined ? "" : String(i[key]);
  const value = opt.number ? decimalText(raw) : raw;
  const id = "f-" + key;
  const common = {
    id,
    readonly: !!opt.locked,
    onBlur: saveSoon,
    onChange: (e) => { editField(key, e.currentTarget.value); saveSoon(); },
  };
  let input;
  if (opt.choices) {
    // English value, label in the chosen language. defaultSelected writes the `selected` attribute as before
    // (Preact's `value` on the select only sets the property).
    const options = [...opt.choices];
    if (value && !options.includes(value)) options.unshift(value);
    input = html`<select ...${common} disabled=${!!opt.locked} value=${value}
        onInput=${(e) => editField(key, e.currentTarget.value)}>
      <option value="">${t("– please choose –")}</option>
      ${options.map((o) => html`<option key=${o} value=${o} defaultSelected=${o === value}>${displayValue(key, o)}</option>`)}
    </select>`;
  } else if (opt.long) {
    input = html`<${TextArea} ...${common} value=${raw} onValue=${(v) => editField(key, v)} />`;
  } else {
    input = html`<${TextInput} ...${common} value=${raw} format=${opt.number ? decimalText : undefined}
        inputmode=${opt.number ? "decimal" : undefined} placeholder=${opt.placeholder}
        onValue=${(v) => editField(key, v)} />`;
  }
  const cls = "field" + (opt.wide ? " wide" : "") + (missing.has(key) ? " is-missing" : "");
  return html`<div key=${key} class=${cls} data-field=${key}>
    <label class="label" for=${id}>${label}${opt.badge || null}<span class="right">
      ${opt.counter ? html`<span id=${"count-" + key}>${charCount(value.length)}</span>` : null}
      ${opt.copy === false ? null
        : html`<button class="btn small" type="button" title=${t("Copy to clipboard")} data-key=${"copy-" + key}
            onClick=${() => copyText(document.getElementById(id).value, label)}>${t("Copy")}</button>`}
    </span></label>
    ${input}
    ${opt.help ? html`<div class="help">${opt.help}</div>` : null}
  </div>`;
}

// EN/DE badge when a listing's title/description is in another language than the setting for new analyses
function languageBadge(i, key, settings) {
  if (!String(i[key] || "").trim()) return null;
  const lang = i[key + "_language"] || "en", setting = settings[key + "_language"];
  if (lang === setting) return null;
  const vars = { lang: langName(lang), setting: langName(setting) };
  return html`<span class="lang-badge" title=${key === "title"
    ? t("This title is in {lang}; new analyses write titles in {setting}.", vars)
    : t("This description is in {lang}; new analyses write descriptions in {setting}.", vars)}>${String(lang).toUpperCase()}</span>`;
}

// Help under the price: suggestion buttons, Vinted's suggestion, the research
function priceHelp(i) {
  const vp = i.vinted_price;
  const locked = LOCKED.has(i.status);
  return [
    locked ? null : html`<div class="tools" style="margin:2px 0 4px"><${PriceChoices} listing=${i} /></div>`,
    vp ? html`<div><strong>${t("Vinted suggests:")}</strong>${" "}${t("{bargain} bargain · {optimal} optimal · {premium} premium",
      { bargain: euro(vp.bargain), optimal: euro(vp.optimal), premium: euro(vp.premium) })}${vp.date ? " " + t("(read on {date})", { date: dateText(vp.date) }) : ""}</div>`
      : html`<div>${t("Vinted’s suggestion has not been fetched yet (view “Prices” → “Fetch Vinted prices”).")}</div>`,
    i.price_reasoning ? html`<div><strong>${t("Research:")}</strong>${" "}${i.price_reasoning}</div>` : null,
  ];
}

// missing: Set of field keys marked red (from missingItems; empty for locked listings)
export function Fields({ listing: i, conditions, packages, settings, missing }) {
  const g = { locked: LOCKED.has(i.status) };
  const o = (extra) => Object.assign(extra, g);
  return html`<div class="card"><h3>${t("Listing")}</h3>
    <div class="grid">
      ${field(i, "title", t("Title"), o({ wide: true, counter: true, badge: languageBadge(i, "title", settings) }), missing)}
      ${field(i, "description", t("Description"), o({ wide: true, long: true, counter: true, badge: languageBadge(i, "description", settings) }), missing)}
      ${field(i, "category", t("Category"), o({ wide: true, placeholder: t("e.g. Women > Shoes > Boots > Ankle boots"), help: t("Use Vinted’s category names, separate levels with >") }), missing)}
      ${field(i, "brand", t("Brand"), o({ placeholder: t("e.g. Levi's – no brand: No brand") }), missing)}
      ${field(i, "size", t("Size (EU)"), o({ placeholder: t("e.g. 39") }), missing)}
      ${field(i, "condition", t("Condition"), o({ choices: conditions || [], copy: false }), missing)}
      ${field(i, "color", t("Colour"), o({}), missing)}
      ${field(i, "material", t("Material"), o({ help: t("optional") }), missing)}
      ${field(i, "shape", t("Shoe shape"), o({ placeholder: t("e.g. Chelsea boot, round toe, block heel"), help: t("optional") }), missing)}
      ${field(i, "heel_height", t("Heel height"), o({ placeholder: t("e.g. approx. 6 cm"), help: t("optional, estimated from the photo – best to measure it") }), missing)}
      ${field(i, "package", t("Package size"), o({ choices: packages || [], copy: false }), missing)}
      ${field(i, "price", t("Price (€)"), o({ number: true, help: priceHelp(i) }), missing)}
      ${field(i, "min_price", t("Minimum price (€), only for you"), o({ number: true, copy: false, help: t("Decline offers below this") }), missing)}
      ${field(i, "notes", t("Note, only for you"), { wide: true, copy: false }, missing)}
    </div>
  </div>`;
}
