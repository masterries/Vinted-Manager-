// Per-browser conveniences in localStorage (keys "vh_<name>": vh_lang, vh_view, vh_filter, vh_metric).
// Storage can be blocked (private window, file://): reads then return null and writes do nothing.

export function remember(name, value) {
  try {
    if (value === undefined) return localStorage.getItem("vh_" + name);
    localStorage.setItem("vh_" + name, value);
  } catch (e) {
    return null;
  }
  return undefined;
}
