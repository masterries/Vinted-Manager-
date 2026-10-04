// Puts selected names on `window` for the browser regression tests and for debugging in the console.
// App code never reads these globals; it imports modules. See "Test bridge" in docs/FRONTEND.md.

// exposeFunctions({ name: fn, ... }): window.name = fn
export function exposeFunctions(functions) {
  for (const [name, fn] of Object.entries(functions)) {
    Object.defineProperty(window, name, { value: fn, configurable: true, writable: true });
  }
}

// exposeState(name, get, set?): window.name reads get(); a plain assignment `name = x` in the console/tests calls set(x)
export function exposeState(name, get, set) {
  Object.defineProperty(window, name, { get, set: set || (() => {}), configurable: true });
}
