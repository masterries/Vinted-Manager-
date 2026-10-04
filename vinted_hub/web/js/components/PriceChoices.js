// Price suggestion buttons (research suggestion + Vinted's bargain/optimal/premium). Used in the listing detail
// (inside div.tools) and in the Prices table (inside div.choices); the container belongs to the caller.
// Returns an array of up to four buttons (null where a value is missing, so positions stay stable).
import { html } from "../lib/preact.js";
import { t } from "../i18n.js";
import { euro } from "../util/format.js";
import { setPrice } from "../state/index.js";

export function PriceChoices({ listing }) {
  const vp = listing.vinted_price || {};
  const button = (value, text, key) => (value
    ? html`<button class="btn small" title=${t("Use as price")} data-key=${`price-choice:${listing.folder}:${key}`}
        onClick=${() => setPrice(listing.folder, value)}>${text}</button>`
    : null);
  return [button(listing.suggested_price, t("Suggestion {price}", { price: euro(listing.suggested_price) }), "suggested"),
    button(vp.bargain, t("{price} bargain", { price: euro(vp.bargain) }), "bargain"),
    button(vp.optimal, t("{price} optimal", { price: euro(vp.optimal) }), "optimal"),
    button(vp.premium, t("{price} premium", { price: euro(vp.premium) }), "premium")];
}
