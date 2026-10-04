// The two numbers the statistics charts can show. Colours: views = --viz-1 (blue), favourites = --viz-2 (orange),
// checked for colour-vision deficiency in light and dark mode (tokens in css/stats.css). One axis per chart only.
import { html } from "../../lib/preact.js";
import { t } from "../../i18n.js";

// Keys are the JSON names ("favorites" as stored by the stats command); the texts are British English.
export const metrics = () => ({
  views: { name: t("Views"), unit: t("views"), total: t("Total views per fetch"), perListing: t("Views per listing"), color: "var(--viz-1)" },
  favorites: { name: t("Favourites"), unit: t("favourites"), total: t("Total favourites per fetch"), perListing: t("Favourites per listing"), color: "var(--viz-2)" },
});

// Short coloured line in front of a label (legend). `color` is one of the --viz tokens above, never data.
export function Swatch({ color }) {
  return html`<span class="swatch" style=${`background:${color}`}></span>`;
}
