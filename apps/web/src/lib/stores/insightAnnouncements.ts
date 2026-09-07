/**
 * Coordinates layout-level insight announcement modals so they never stack.
 * Weekly digest takes priority over the daily “new insights” sheet.
 */
import { writable } from 'svelte/store';

export const weeklyDigestModalOpen = writable(false);
