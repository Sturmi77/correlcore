/**
 * In-flight Health Connect Sync now tracking (session-drain hook).
 *
 * Kept free of API/auth/env imports so offline session drain can await HC
 * Sync now without pulling the native bridge graph into every session import.
 */

let healthConnectSyncInFlight: Promise<unknown> | null = null;

/** Register the active Sync now promise (cleared in ``finally``). */
export function trackHealthConnectSyncInFlight(run: Promise<unknown>): void {
  healthConnectSyncInFlight = run.finally(() => {
    if (healthConnectSyncInFlight === run) {
      healthConnectSyncInFlight = null;
    }
  });
}

/** Await any in-flight HC Sync now before swapping session credentials. */
export async function drainHealthConnectSyncForSessionChange(): Promise<void> {
  const inFlight = healthConnectSyncInFlight;
  if (!inFlight) return;
  try {
    await inFlight;
  } catch {
    // Failures are already mapped to sync statuses; session transition proceeds.
  }
}

/** Test-only: drop in-flight tracking between cases. */
export function _resetHealthConnectSyncLifecycleForTests(): void {
  healthConnectSyncInFlight = null;
}
