// Read-only helpers on the state (no changes, no notify). Safe to call during render.
import { state } from "./store.js";

export const listings = () => (state.data ? state.data.listings : []);
export const byFolder = (folder) => listings().find((i) => i.folder === folder);
export const visibleListings = () => listings().filter((i) => state.filter === "all" || i.status === state.filter);
export const currentListing = () => (state.current ? byFolder(state.current) : undefined);
export const jobRunning = () => !!(state.live.job && state.live.job.running);
