// The only module that imports the vendored library (Preact 10 + htm 3.1.1, "htm/preact/standalone").
// Everything else imports from here, so updating vendor/preact-htm.js touches nothing else (see docs/FRONTEND.md).
export {
  h, html, render, Component, createContext,
  useState, useReducer, useEffect, useLayoutEffect, useRef, useImperativeHandle,
  useMemo, useCallback, useContext, useErrorBoundary,
} from "../../vendor/preact-htm.js";

// The standalone build has no Fragment export: a component returns an array for several top-level elements.
