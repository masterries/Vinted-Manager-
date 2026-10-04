// Full-size photo viewer. A click anywhere closes it; the keys (Esc, ← →) are handled in keyboard.js.
import { html } from "../lib/preact.js";
import { t } from "../i18n.js";
import { imageUrl } from "../api.js";
import { photoOrder } from "../domain/listing.js";
import { useStore, byFolder, closeLightbox } from "../state/index.js";

export function Lightbox() {
  const s = useStore();
  const lb = s.lightbox;
  const i = lb.folder ? byFolder(lb.folder) : null;
  const file = i ? photoOrder(i)[lb.index] : undefined;
  return html`<div id="lightbox" class="lightbox" hidden=${!lb.open} title=${t("Click or Esc to close · ← → more photos")}
      onClick=${closeLightbox}>
    <img src=${file ? imageUrl(lb.folder, file, 1600) : undefined} alt=${file || ""} />
  </div>`;
}
