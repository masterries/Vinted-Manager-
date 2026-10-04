// Settings dialog (native modal <dialog>: focus stays inside, Esc closes). Three languages: interface, titles and
// descriptions of new analyses; plus read-only info from config.json. Every choice is saved at once (changeSetting).
// The content exists only while the dialog is open (built in the language current then). While open, the toast is
// rendered inside the dialog, because a modal dialog covers everything outside it.
import { html, useLayoutEffect, useRef } from "../lib/preact.js";
import { t, tn, langName } from "../i18n.js";
import { languageMismatch } from "../domain/listing.js";
import { useStore, listings, changeSetting, closeSettings } from "../state/index.js";
import { Toast } from "./Toast.js";

const NATIVE_NAME = { de: "Deutsch", en: "English" };   // each language in its own language, never translated

// Hint under the language rows: listings not yet on Vinted whose texts are in another language than the settings
function mismatchNote(s) {
  if (!s.data) return null;
  const mm = languageMismatch(listings(), s.settings);
  const titleLang = langName(s.settings.title_language), descriptionLang = langName(s.settings.description_language);
  if (!mm.title && !mm.description) return html`<div class="box ok set-note">${t("All listings not yet on Vinted match these settings.")}</div>`;
  const command = mm.title && mm.description
    ? (s.settings.title_language === s.settings.description_language ? t("Rewrite the listings in {lang}", { lang: titleLang })
      : t("Rewrite the titles in {title} and the descriptions in {description}", { title: titleLang, description: descriptionLang }))
    : mm.title ? t("Rewrite the titles in {lang}", { lang: titleLang }) : t("Rewrite the descriptions in {lang}", { lang: descriptionLang });
  const titles = mm.title, descriptions = mm.description;
  return html`<div class="box hint set-note">
    ${titles ? html`<div>${tn(titles, "{n} listing not yet on Vinted has a title that is not in {lang}.",
      "{n} listings not yet on Vinted have a title that is not in {lang}.", { lang: titleLang })}</div>` : null}
    ${descriptions ? html`<div>${tn(descriptions, "{n} listing not yet on Vinted has a description that is not in {lang}.",
      "{n} listings not yet on Vinted have a description that is not in {lang}.", { lang: descriptionLang })}</div>` : null}
    <div>${t("The hub can’t translate by itself. Ask Claude: “{command}”.", { command })}</div>
  </div>`;
}

function content(s) {
  // One choice button; langAttr marks a language name written in its own language
  const choice = (key, value, text, langAttr) => html`<button key=${value} type="button" aria-pressed=${String(s.settings[key] === value)}
      lang=${langAttr} data-key=${`set-${key}-${value}`} onClick=${() => changeSetting(key, value)}>${text}</button>`;
  const group = (labelId, buttons) => html`<div class="segmented" role="group" aria-labelledby=${labelId}>${buttons}</div>`;
  const listingRow = (key, label) => html`<div class="set-row">
    <span id=${`set-${key}-label`}>${label}</span>
    ${group(`set-${key}-label`, (s.choices[key] || []).map((v) => choice(key, v, langName(v))))}
  </div>`;
  const info = s.settingsInfo;
  const infoRows = info ? [[t("Vinted site"), info.domain], [t("Data folder"), info.data_folder], [t("Photo input folder"), info.input_folder],
    [t("Hub port"), info.hub_port], [t("Chrome port"), info.chrome_port]] : [];
  return [
    html`<div class="dialog-head">
      <h2 id="settings-title">${t("Settings")}</h2>
      <button type="button" class="btn" aria-label=${t("Close")} title=${t("Close")} data-key="set-close" onClick=${closeSettings}>✕</button>
    </div>`,
    html`<section aria-labelledby="set-ui">
      <h3 id="set-ui">${t("Interface language")}</h3>
      ${group("set-ui", (s.choices.ui_language || []).map((v) => choice("ui_language", v, NATIVE_NAME[v] || v, v)))}
    </section>`,
    html`<section aria-labelledby="set-texts">
      <h3 id="set-texts">${t("Listing texts")}</h3>
      <p class="help">${t("Applies to new analyses by Claude. Existing listings are not changed automatically.")}</p>
      ${listingRow("title_language", t("Title language"))}
      ${listingRow("description_language", t("Description language"))}
      ${mismatchNote(s)}
    </section>`,
    html`<section aria-labelledby="set-info">
      <h3 id="set-info">${t("Info")}</h3>
      ${info
        ? html`<dl class="info-list">${infoRows.flatMap(([label, value]) =>
            [html`<dt>${label}</dt>`, html`<dd>${value === null || value === undefined || value === "" ? "–" : String(value)}</dd>`])}</dl>`
        : html`<p class="help">${s.settingsError ? t("Could not load settings: {error}", { error: s.settingsError }) : t("Loading …")}</p>`}
      ${info ? html`<p class="help">${t("Set in config.json (shown here for information only).")}</p>` : null}
    </section>`,
  ];
}

export function SettingsDialog() {
  const s = useStore();
  const ref = useRef(null);
  const backdropDown = useRef(false);

  // state.settingsOpen drives the native dialog: open it modally and focus the chosen interface language, or close it
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (s.settingsOpen) {
      if (!dialog.open) {
        if (typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open", "");
      }
      const first = dialog.querySelector('[data-key^="set-ui_language-"][aria-pressed="true"]') || dialog.querySelector("button");
      if (first) first.focus();
    } else if (dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else { dialog.removeAttribute("open"); dialog.dispatchEvent(new Event("close")); }
    }
  }, [s.settingsOpen]);

  // Closed by Esc, ✕ or the backdrop: forget the open state and give the focus back to the gear button
  const onClose = () => {
    closeSettings();
    const button = document.getElementById("settings-button");
    if (button) button.focus();
  };
  // A click on the dark backdrop closes (the dialog has no padding, so a click on the element itself is outside the content)
  const onPointerDown = (e) => { backdropDown.current = e.target === e.currentTarget; };
  const onClick = (e) => {
    if (e.target === e.currentTarget && backdropDown.current) closeSettings();
    backdropDown.current = false;
  };

  return html`<dialog id="settings" class="dialog" aria-labelledby="settings-title" ref=${ref}
      onClose=${onClose} onPointerDown=${onPointerDown} onClick=${onClick}>
    <div id="settings-body" class="dialog-body">${s.settingsOpen ? content(s) : null}</div>
    ${s.settingsOpen ? html`<${Toast} />` : null}
  </dialog>`;
}
