/**
 * Auto-Save state machine — ADR-0013.
 *
 * Pure logic kept out of any Svelte component so it is unit-testable
 * with plain Vitest (no jsdom Svelte life-cycle, no msw network).
 *
 * State graph:
 *
 *   idle → (markDirty) → dirty → (debounce 800 ms) → saving
 *                                                       │
 *                                  ┌─── success ────────┼─── error
 *                                  ▼                                 ▼
 *                                saved (auto-back to idle after 5 s)   error
 *                                  │                                 │
 *                                  └── markDirty                     └── markDirty / retry → dirty
 *
 * Highlights from ADR-0013:
 *  - 800 ms debounce window
 *  - while `saving`, further `markDirty` calls are buffered: the next
 *    save kicks off automatically once the in-flight call returns
 *    (re-flush) — no overlapping POST/PATCH requests
 *  - `saved` state auto-reverts to `idle` after 5 s so the badge fades
 *  - error state surfaces a `lastError` for the UI; `retry()` jumps
 *    straight to `saving` again with the current snapshot
 *  - all timers go through injected `setTimeout`/`clearTimeout`
 *    references so tests can use `vi.useFakeTimers()`
 *
 * The host component owns the actual save function (POST or PATCH +
 * tag/symptom replace-set) and the form snapshot; this controller only
 * orchestrates *when* to call it.
 */

import { writable, type Readable, get } from 'svelte/store';

export type AutoSaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export interface AutoSaveState {
  status: AutoSaveStatus;
  /** Wall-clock timestamp (ms since epoch) of the last successful save. */
  lastSavedAt: number | null;
  /** Surface the most recent error so the UI can show "Retry?". */
  lastError: string | null;
}

export interface AutoSaveOptions<T> {
  /** Snapshot the current form. Called right before each save. */
  getSnapshot: () => T;
  /** Persist a snapshot. Resolves on success, rejects on failure. */
  // eslint-disable-next-line no-unused-vars
  save: (snapshot: T) => Promise<void>;
  /** Debounce window in ms. ADR-0013 mandates 800. */
  debounceMs?: number;
  /** How long the `saved` badge stays visible before reverting to `idle`. */
  savedDisplayMs?: number;
  /** Hook for tests to swap the timer impl. */
  setTimeoutFn?: typeof setTimeout;
  clearTimeoutFn?: typeof clearTimeout;
  /** Wall-clock provider (tests inject a fake). */
  now?: () => number;
}

export interface AutoSaveController<T> {
  /** Reactive state for UI bindings. */
  state: Readable<AutoSaveState>;
  /** Mark the form as dirty — schedules a save after the debounce window. */
  markDirty: () => void;
  /**
   * Force an immediate flush of any pending save (no debounce wait).
   * Used by `beforeunload` to give the browser a chance to persist.
   */
  flushNow: () => Promise<void>;
  /** Manual retry from the `error` state. */
  retry: () => Promise<void>;
  /**
   * Hard reset to `idle`. Cancels pending timers. Useful when the user
   * navigates to a different date and the form is re-hydrated.
   */
  reset: () => void;
  /** Tear down all timers — call from `onDestroy`. */
  destroy: () => void;
  /** Test helper: read the current state synchronously. */
  peek: () => AutoSaveState;
  // For tests / advanced UIs.
  _getSnapshot: () => T;
}

const DEFAULT_DEBOUNCE = 800;
const DEFAULT_SAVED_DISPLAY = 5000;

export function createAutoSave<T>(opts: AutoSaveOptions<T>): AutoSaveController<T> {
  const debounceMs = opts.debounceMs ?? DEFAULT_DEBOUNCE;
  const savedDisplayMs = opts.savedDisplayMs ?? DEFAULT_SAVED_DISPLAY;
  const setT = opts.setTimeoutFn ?? setTimeout;
  const clearT = opts.clearTimeoutFn ?? clearTimeout;
  const now = opts.now ?? Date.now;

  const initial: AutoSaveState = { status: 'idle', lastSavedAt: null, lastError: null };
  const store = writable<AutoSaveState>(initial);

  let debounceHandle: ReturnType<typeof setTimeout> | null = null;
  let savedFadeHandle: ReturnType<typeof setTimeout> | null = null;
  // Re-flush flag: a markDirty arrived while a save was in flight.
  let bufferedDirty = false;
  // Set true on `destroy` so late-resolving promises don't mutate state.
  let disposed = false;

  function clearDebounce() {
    if (debounceHandle !== null) {
      clearT(debounceHandle);
      debounceHandle = null;
    }
  }

  function clearSavedFade() {
    if (savedFadeHandle !== null) {
      clearT(savedFadeHandle);
      savedFadeHandle = null;
    }
  }

  function setStatus(patch: Partial<AutoSaveState>) {
    if (disposed) return;
    store.update((s) => ({ ...s, ...patch }));
  }

  async function runSave() {
    if (disposed) return;
    const current = get(store);
    if (current.status === 'saving') {
      // Already running — set buffered flag and let the in-flight save
      // pick up the next snapshot when it returns.
      bufferedDirty = true;
      return;
    }
    setStatus({ status: 'saving', lastError: null });
    let snapshot: T;
    try {
      snapshot = opts.getSnapshot();
    } catch (err) {
      setStatus({
        status: 'error',
        lastError: err instanceof Error ? err.message : String(err),
      });
      return;
    }
    try {
      await opts.save(snapshot);
      if (disposed) return;
      if (bufferedDirty) {
        bufferedDirty = false;
        // Re-flush: a change happened while we were saving. Keep the
        // user's mental model intact — go back to dirty and schedule
        // another debounced save.
        setStatus({ status: 'dirty', lastError: null });
        scheduleDebounced();
        return;
      }
      setStatus({ status: 'saved', lastSavedAt: now(), lastError: null });
      clearSavedFade();
      savedFadeHandle = setT(() => {
        savedFadeHandle = null;
        // Only fade back to idle if no further edits happened in the
        // meantime (status would be `dirty` or `saving` then).
        const s = get(store);
        if (s.status === 'saved') setStatus({ status: 'idle' });
      }, savedDisplayMs);
    } catch (err) {
      if (disposed) return;
      bufferedDirty = false;
      setStatus({
        status: 'error',
        lastError: err instanceof Error ? err.message : String(err),
      });
    }
  }

  function scheduleDebounced() {
    clearDebounce();
    debounceHandle = setT(() => {
      debounceHandle = null;
      void runSave();
    }, debounceMs);
  }

  function markDirty() {
    if (disposed) return;
    const cur = get(store);
    if (cur.status === 'saving') {
      // Mark the buffer; the running save will re-flush on completion.
      bufferedDirty = true;
      return;
    }
    // Any prior `saved` fade is now obsolete — the user is editing again.
    clearSavedFade();
    setStatus({ status: 'dirty' });
    scheduleDebounced();
  }

  async function flushNow() {
    clearDebounce();
    const cur = get(store);
    if (cur.status === 'dirty' || cur.status === 'error') {
      await runSave();
    }
  }

  async function retry() {
    clearDebounce();
    const cur = get(store);
    if (cur.status === 'error' || cur.status === 'dirty') {
      await runSave();
    }
  }

  function reset() {
    clearDebounce();
    clearSavedFade();
    bufferedDirty = false;
    setStatus({ status: 'idle', lastError: null });
  }

  function destroy() {
    clearDebounce();
    clearSavedFade();
    disposed = true;
  }

  return {
    state: { subscribe: store.subscribe },
    markDirty,
    flushNow,
    retry,
    reset,
    destroy,
    peek: () => get(store),
    _getSnapshot: opts.getSnapshot,
  };
}
