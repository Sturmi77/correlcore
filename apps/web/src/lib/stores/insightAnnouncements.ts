/**
 * Coordinates layout-level insight announcement modals so they never stack.
 * Weekly digest takes priority over the daily “new insights” sheet.
 */
import { writable } from 'svelte/store';

export const weeklyDigestModalOpen = writable(false);

/**
 * Flips true after WeeklyDigestModal finishes its eligibility check (whether
 * it opens or skips). NewInsightsModal waits on this so a fixed timer cannot
 * race ahead of a slow digest prefs/digest fetch.
 */
export const weeklyDigestEligibilitySettled = writable(false);
