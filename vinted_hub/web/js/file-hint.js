/* Classic script, deliberately NOT a module: browsers block ES modules on file:// pages, so when index.html is
   opened as a file (double-click) the app cannot start. This script still runs there and explains how to start the hub.
   Over http it does nothing. Its texts have their own small dictionary below (tools/check_i18n.py checks this file
   against FILE_HINT_DE only). */
"use strict";

const FILE_HINT_DE = {
  "Vinted Hub": "Vinted Zentrale",
  "Please don’t open this page as a file": "Bitte nicht als Datei öffnen",
  "This page needs the small local server. Start it by double-clicking “Start Hub.bat” in the project folder (or: python -m vinted_hub serve). The page then opens by itself at http://127.0.0.1:8765.": "Diese Seite braucht den kleinen lokalen Server. Starte ihn per Doppelklick auf „Start Hub.bat“ im Projektordner (oder: python -m vinted_hub serve). Dann öffnet sich die Seite unter http://127.0.0.1:8765 von selbst.",
};

if (location.protocol === "file:") {
  let lang = null;
  try { lang = localStorage.getItem("vh_lang"); } catch (e) { lang = null; }
  if (lang !== "en" && lang !== "de") lang = /^de\b/i.test(navigator.language || "") ? "de" : "en";
  const t = (text) => (lang === "de" && Object.prototype.hasOwnProperty.call(FILE_HINT_DE, text) ? FILE_HINT_DE[text] : text);
  const el = (tag, className, ...children) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.append(...children);
    return node;
  };
  const show = () => {
    document.documentElement.lang = lang;
    document.title = t("Vinted Hub");
    const title = el("h1", null, t("Vinted Hub"));
    title.id = "app-name";
    const detail = el("section", "detail",
      el("div", "box missing", el("h3", null, t("Please don’t open this page as a file")),
        t("This page needs the small local server. Start it by double-clicking “Start Hub.bat” in the project folder (or: python -m vinted_hub serve). The page then opens by itself at http://127.0.0.1:8765.")));
    detail.id = "detail";
    // the old page's skeleton: an empty list column, the hint in the wide detail column
    const list = el("aside", "list");
    list.id = "list";
    document.body.append(el("header", "header", title), el("main", "layout", list, detail));
    // phone layout (below 820 px): show the detail column, not the empty list
    document.body.classList.add("mobile-detail");
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", show);
  else show();
}
