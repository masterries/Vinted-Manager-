/* ---------- Prices view ----------
   Children of <section id="table-view"> (App renders the section): view header with "Fetch Vinted prices" and a
   table of all listings that are not sold - Vinted's suggestion, suggestion buttons, price and minimum price.
   Typing goes through editPrice() (written into the listing at once, saved 700 ms later; an invalid number stays
   in the field but is not sent); leaving a field saves at once. The fields keep caret and text across re-renders
   (status poll, language switch) because they are TextInputs and every row is keyed by folder. */
import { html } from "../../lib/preact.js";
import { t, fmtNum, displayValue } from "../../i18n.js";
import { num, euro, decimalText } from "../../util/format.js";
import { LOCKED, EMPTY, fieldName } from "../../domain/listing.js";
import { imageUrl } from "../../api.js";
import { useStore, editPrice, saveNow, startJob, showView } from "../../state/index.js";
import { TextInput } from "../../components/inputs.js";
import { StatusPill } from "../../components/Badges.js";
import { PriceChoices } from "../../components/PriceChoices.js";

// Price or minimum price of one listing (read-only once the listing is on Vinted)
function NumberField({ listing: i, field }) {
  return html`<${TextInput} inputmode="decimal" readonly=${LOCKED.has(i.status)} aria-label=${fieldName(field)}
    data-key=${`price-input:${i.folder}:${field}`} class=${field === "price" && !(num(i.price) > 0) ? "empty" : null}
    placeholder=${field === "price" ? t("Price") : t("optional")}
    value=${i[field]} format=${decimalText} onValue=${(v) => editPrice(i.folder, field, v)}
    onBlur=${() => saveNow().catch(() => {})} />`;
}

// "Brand · Size 39 · Very good" under the title (unknown values left out)
function facts(i) {
  return [displayValue("brand", i.brand), !EMPTY.test(i.size ?? "") && t("Size {size}", { size: i.size }),
    displayValue("condition", i.condition)].filter((x) => x && !EMPTY.test(x)).join(" · ");
}

function vintedPrices(i) {
  const vp = i.vinted_price;
  return vp ? `${euro(vp.bargain)} / ${euro(vp.optimal)} / ${euro(vp.premium)}` : html`<span class="small">${t("not fetched yet")}</span>`;
}

export function PricesView() {
  const s = useStore();
  if (!s.data) return null;
  const list = s.data.listings.filter((i) => i.status !== "sold");
  const withPrice = list.filter((i) => num(i.price) > 0);
  const total = (get) => list.reduce((sum, i) => sum + (num(get(i)) || 0), 0);
  const head = ["", t("Listing"), t("Status"), t("Vinted"), t("Use"), t("Price €"), t("Minimum price €")];
  return html`<div class="view-header">
      <div class="text">${t("Set your prices here. Click a suggestion to use it, or type your own.")} ${t("“Suggestion” comes from the research; the three Vinted values (bargain / optimal / premium) come from Vinted’s own suggestion.")}</div>
      <button class="btn" data-key="fetch-prices" onClick=${() => startJob("prices")}
        title=${t("In the Vinted Chrome, fills in only category, brand, size and condition, reads the suggestion and closes the tab without saving")}>${t("Fetch Vinted prices")}</button>
    </div>
    <div class="table-frame"><table class="table">
      <thead><tr>${head.map((label) => html`<th>${label}</th>`)}</tr></thead>
      <tbody>${list.map((i) => html`<tr key=${i.folder}>
        <td>${(i.photos || [])[0] ? html`<img src=${imageUrl(i.folder, i.photos[0], 360)} alt="" loading="lazy" />` : null}</td>
        <td><div class="title-link" onClick=${() => showView("listings", i.folder)}>${i.title || i.folder}</div><div class="small">${facts(i)}</div></td>
        <td><${StatusPill} status=${i.status} /></td>
        <td style="white-space:nowrap">${vintedPrices(i)}</td>
        <td>${LOCKED.has(i.status) ? null : html`<div class="choices"><${PriceChoices} listing=${i} /></div>`}</td>
        <td><${NumberField} listing=${i} field="price" /></td>
        <td><${NumberField} listing=${i} field="min_price" /></td>
      </tr>`)}</tbody>
      <tfoot><tr><td></td><td>${t("{n} of {total} with a price", { n: fmtNum(withPrice.length), total: fmtNum(list.length) })}</td><td></td><td></td><td></td>
        <td>${euro(Math.round(total((i) => i.price) * 100) / 100)}</td>
        <td>${euro(Math.round(total((i) => i.min_price) * 100) / 100)}</td></tr></tfoot>
    </table></div>`;
}
