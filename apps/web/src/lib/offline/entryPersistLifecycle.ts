/**
 * In-flight EntryForm persist tracking (session-drain hook).
 *
 * Kept free of API/auth/component imports so offline session drain can await
 * entry autosaves without pulling the EntryForm graph into every session import.
 *
 * login()/logout() await this before swapping cookies/Bearer so a slow
 * persist (e.g. onboarding finalize, relation re-fetch) cannot resume under
 * the next account and write the prior user's snapshot into their entries.
 */

let entryPersistInFlight: Promise<unknown> | null = null;

/** Register the active entry persist promise (cleared in ``finally``). */
export function trackEntryPersistInFlight(run: Promise<unknown>): void {
  entryPersistInFlight = run.finally(() => {
    if (entryPersistInFlight === run) {
      entryPersistInFlight = null;
    }
  });
}

/** Await any in-flight entry persist before swapping session credentials. */
export async function drainEntryPersistForSessionChange(): Promise<void> {
  const inFlight = entryPersistInFlight;
  if (!inFlight) return;
  try {
    await inFlight;
  } catch {
    // Failures are already mapped to autosave error state; session transition proceeds.
  }
}

/** Test-only: drop in-flight tracking between cases. */
export function _resetEntryPersistLifecycleForTests(): void {
  entryPersistInFlight = null;
}
