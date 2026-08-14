/**
 * In-flight Health Connect Sync now tracking (session-drain hook).
 *
 * Kept free of API/auth/env imports so offline session drain can await HC
 * Sync now without pulling the native bridge graph into every session import.
 *
 * The tracker holds *every* concurrent sync, not just the most recent one. A
 * user can start "Sync now", navigate away and back while the native read is
 * still running, and start a second sync (the `syncing` flag is component-local),
 * so two syncs overlap. A single-slot registry would drain only the newest and
 * let the older one settle — and its post-import Dexie fill / scheduleSync() —
 * after the session drain, under the next account.
 */

const inFlight = new Set<Promise<unknown>>();

/** Register an active Sync now promise (removed once it settles). */
export function trackHealthConnectSyncInFlight(run: Promise<unknown>): void {
  inFlight.add(run);
  // then(onFulfilled, onRejected) rather than finally()+void: a rejected sync
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
 * Await every in-flight HC Sync now before swapping session credentials.
 *
 * Loops until the set is empty: awaiting one batch can surface a sync that was
 * registered after the snapshot was taken (an overlapping run that had not
 * started when draining began), so a single `allSettled` pass is not enough to
 * guarantee quiescence.
 */
export async function drainHealthConnectSyncForSessionChange(): Promise<void> {
  while (inFlight.size > 0) {
    // Failures are already mapped to sync statuses; session transition proceeds
    // regardless, so allSettled (never rejecting) is what we want.
    await Promise.allSettled([...inFlight]);
  }
}

/** Test-only: drop in-flight tracking between cases. */
export function _resetHealthConnectSyncLifecycleForTests(): void {
  inFlight.clear();
}
