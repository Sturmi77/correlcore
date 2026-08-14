/**
 * In-flight EntryForm persist tracking (session-drain hook).
 *
 * Kept free of API/auth/component imports so offline session drain can await
 * entry autosaves without pulling the EntryForm graph into every session import.
 *
 * login()/logout() await this before swapping cookies/Bearer so a slow
 * persist (e.g. onboarding finalize, relation re-fetch) cannot resume under
 * the next account and write the prior user's snapshot into their entries.
 *
 * The tracker holds *every* concurrent persist, not just the most recent one.
 * `EntrySheet` can remount its keyed `EntryForm` for another date while the
 * destroyed form's `autoSave.destroy()` leaves an `opts.save` still running, so
 * two persists overlap. A single-slot registry would forget the older one and
 * let it settle *after* the session drain — resuming under the next account.
 */

const inFlight = new Set<Promise<unknown>>();

/** Register an active entry persist promise (removed once it settles). */
export function trackEntryPersistInFlight(run: Promise<unknown>): void {
  inFlight.add(run);
  // then(onFulfilled, onRejected) rather than finally()+void: a rejected save
  // must not leave an unhandled rejection on a floating wrapper promise when
  // nobody is currently draining.
  void run.then(
    () => {
      inFlight.delete(run);
    },
    () => {
      inFlight.delete(run);
    }
  );
}

/**
 * Await every in-flight entry persist before swapping session credentials.
 *
 * Loops until the set is empty: awaiting one batch can surface a persist that
 * was registered after the snapshot was taken (an overlapping save that had
 * not started when draining began), so a single `allSettled` pass is not
 * enough to guarantee quiescence.
 */
export async function drainEntryPersistForSessionChange(): Promise<void> {
  while (inFlight.size > 0) {
    // Failures are already mapped to autosave error state; session transition
    // proceeds regardless, so allSettled (never rejecting) is what we want.
    await Promise.allSettled([...inFlight]);
  }
}

/** Test-only: drop in-flight tracking between cases. */
export function _resetEntryPersistLifecycleForTests(): void {
  inFlight.clear();
}
