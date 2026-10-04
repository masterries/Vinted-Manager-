// The "Photos" card: chosen photos in upload order (first = cover photo) with move/remove buttons, then the unused
// photos of the folder with "+ use". A click on a photo opens the viewer. Changes are saved at once (setPhotos).
// The detail is rebuilt for every listing switch (ListingsMain keys it by the listing). Images that are removed keep
// downloading in the browser, so when the card goes away it drops their src: quickly stepping through listings (↑/↓
// held, previews not generated yet) then does not pile up slow image requests that block the browser's few connections
// to the hub (saves, polls, statistics); without it the requests of every listing passed would stay open.
import { html, useLayoutEffect, useRef } from "../../lib/preact.js";
import { t, fmtNum } from "../../i18n.js";
import { imageUrl } from "../../api.js";
import { setPhotos, openLightbox } from "../../state/index.js";

function photo(i, file, idx, off, chosen, locked) {
  const swap = (a, b) => { const n = [...chosen]; [n[a], n[b]] = [n[b], n[a]]; setPhotos(i.folder, n); };
  return html`<div key=${file} class=${"photo" + (off ? " off" : "")}>
    <img src=${imageUrl(i.folder, file, 360)} alt=${file} loading="lazy" title=${file} onClick=${() => openLightbox(i.folder, file)} />
    ${!off && idx === 0 ? html`<span class="cover">${t("Cover photo")}</span>` : null}
    ${locked ? null : html`<div class="controls">${off
      ? [html`<button key="use" class="btn small" data-key=${`photo-use-${file}`} onClick=${() => setPhotos(i.folder, [...chosen, file])}>${t("+ use")}</button>`]
      : [html`<button key="fwd" class="btn small" disabled=${idx === 0} title=${t("move forward")} aria-label=${t("move forward")}
            data-key=${`photo-fwd-${file}`} onClick=${() => swap(idx - 1, idx)}>◀</button>`,
         html`<button key="off" class="btn small" title=${t("don’t use")} aria-label=${t("don’t use")} data-key=${`photo-off-${file}`}
            onClick=${() => setPhotos(i.folder, chosen.filter((f) => f !== file))}>✕</button>`,
         html`<button key="back" class="btn small" disabled=${idx === chosen.length - 1} title=${t("move back")} aria-label=${t("move back")}
            data-key=${`photo-back-${file}`} onClick=${() => swap(idx + 1, idx)}>▶</button>`]}</div>`}
  </div>`;
}

export function Photos({ listing: i, locked, missing }) {
  const chosen = i.photos || [];
  const unused = (i._all_photos || []).filter((f) => !chosen.includes(f));
  const card = useRef(null);
  useLayoutEffect(() => () => {     // on unmount only: stop the downloads of this listing's photos
    if (card.current) for (const img of card.current.querySelectorAll("img")) img.removeAttribute("src");
  }, []);
  return html`<div class=${missing ? "card is-missing" : "card"} data-field="photos" ref=${card}>
    <h3>${t("Photos")}<small>${t("{n} selected · the first one is the cover photo · max. 20", { n: fmtNum(chosen.length) })}</small></h3>
    ${chosen.length
      ? html`<div class="photos">${chosen.map((f, idx) => photo(i, f, idx, false, chosen, locked))}</div>`
      : html`<div class="help">${t("No photos selected.")}</div>`}
    ${unused.length ? html`<div class="help" style="margin:12px 0 6px;color:var(--muted);font-size:13px">${t("Not used")}</div>` : null}
    ${unused.length ? html`<div class="photos">${unused.map((f) => photo(i, f, -1, true, chosen, locked))}</div>` : null}
  </div>`;
}
