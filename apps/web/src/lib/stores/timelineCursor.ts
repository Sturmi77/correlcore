/**
 * TimelineCursor Store — M3.8 Sprint 1 (ADR-0035)
 *
 * Single shared cursor state for the Trends Compare view. All trend
 * components (MetricTimeseries, TagHeatmap, ComparisonHeatmap, future
 * UnifiedStripChart) subscribe to this store and render a vertical
 * cursor line at the same date. Hover / focus / active dispatch
 * helpers keep behaviour identical across components.
 *
 * Cursor state is intentionally NOT persisted — it is interactive
 * UI state that only makes sense during a session.
 */

import { derived, writable, type Readable } from 'svelte/store';

export type CursorSource = 'hover' | 'focus' | 'keyboard' | 'tap' | null;

export interface TimelineCursorState {
  /**
   * Currently hovered/focused ISO date (YYYY-MM-DD). Null when no
   * cursor is shown (mouse left the canvas, no focus).
   */
  date: string | null;
  /**
   * Which interaction produced the current cursor position. Used by
   * components to differentiate styling (e.g. focus ring vs hover halo).
   */
  source: CursorSource;
  /**
   * Stable reference axis for cursor X resolution. Components that
   * share an axis MUST publish their dates here on mount so keyboard
   * navigation (arrow keys) can advance by one day.
   */
  axisDates: readonly string[];
}

const initialState: TimelineCursorState = {
  date: null,
  source: null,
  axisDates: [],
};

function createTimelineCursor() {
  const { subscribe, update, set } = writable<TimelineCursorState>(initialState);

  return {
    subscribe,
    /** Publish or refresh the shared daily axis. */
    setAxis(dates: readonly string[]) {
      update((state) => ({ ...state, axisDates: dates }));
    },
    /** Move the cursor to a specific ISO date. */
    setDate(date: string | null, source: CursorSource = null) {
      update((state) => ({ ...state, date, source }));
    },
    /** Hover handler — only updates if no focus is currently active. */
    hover(date: string | null) {
      update((state) => {
        if (state.source === 'focus' || state.source === 'keyboard') return state;
        return { ...state, date, source: date ? 'hover' : null };
      });
    },
    /** Set focus cursor — wins over hover. */
    focus(date: string | null) {
      update((state) => ({ ...state, date, source: date ? 'focus' : null }));
    },
    /**
     * Advance cursor by N days (negative = backward). Clamps to axis
     * bounds. Returns the resolved new date or null if axis is empty.
     */
    move(delta: number): string | null {
      let result: string | null = null;
      update((state) => {
        if (state.axisDates.length === 0) return state;
        const currentIndex = state.date ? state.axisDates.indexOf(state.date) : -1;
        const startIndex = currentIndex >= 0 ? currentIndex : state.axisDates.length - 1;
        const nextIndex = Math.min(state.axisDates.length - 1, Math.max(0, startIndex + delta));
        const nextDate = state.axisDates[nextIndex] ?? null;
        result = nextDate;
        return { ...state, date: nextDate, source: 'keyboard' };
      });
      return result;
    },
    /** Clear the cursor entirely. */
    clear() {
      update((state) => ({ ...state, date: null, source: null }));
    },
    /** Reset to initial state (used in tests). */
    reset() {
      set(initialState);
    },
  };
}

export const timelineCursor = createTimelineCursor();

/**
 * Convenience selector: just the active ISO date (null when no cursor).
 */
export const timelineCursorDate: Readable<string | null> = derived(timelineCursor, ($s) => $s.date);
