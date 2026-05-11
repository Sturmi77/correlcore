import { writable } from 'svelte/store';

/**
 * Developer mode toggle — in-memory only (no localStorage / sessionStorage).
 * Resets to false on every page reload.
 * When true, the /dev route link becomes visible in Settings regardless
 * of the backend DEV_VIEW_ENABLED flag.
 */
export const developerMode = writable<boolean>(false);
