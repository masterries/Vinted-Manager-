// Entry point of the hub page (loaded by index.html as an ES module; see docs/FRONTEND.md).
// On file:// Chromium refuses ES modules, so this does not even load there; js/file-hint.js (a classic script)
// explains instead. Browsers that do run modules from file:// (Firefox, depending on its settings) stop at the
// protocol check below, so the app never renders next to the hint. (A module cannot `return` at the top level,
// hence the block.)
import "./test-bridge.js";
import { html, render } from "./lib/preact.js";
import { initLanguage } from "./i18n.js";
import { App } from "./components/App.js";
import { installKeyboard } from "./keyboard.js";
import { load, pollStatus, checkVersion, hasPending, saveNow } from "./state/index.js";

if (location.protocol !== "file:") {
  initLanguage();                                   // <html lang> and the tab title, once
  render(html`<${App} />`, document.getElementById("app"));
  installKeyboard();
  // Someone else (e.g. Claude) may have changed listings.json while the tab was in the background
  window.addEventListener("focus", checkVersion);
  document.addEventListener("visibilitychange", checkVersion);
  // Unsaved edits: send them and ask the browser to confirm leaving
  window.addEventListener("beforeunload", (e) => {
    if (hasPending()) { saveNow().catch(() => {}); e.preventDefault(); e.returnValue = ""; }
  });
  load().then(() => pollStatus());
}
