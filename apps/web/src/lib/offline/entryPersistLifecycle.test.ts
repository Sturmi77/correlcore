import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  _resetEntryPersistLifecycleForTests,
  drainEntryPersistForSessionChange,
  trackEntryPersistInFlight,
} from './entryPersistLifecycle';

afterEach(() => {
  _resetEntryPersistLifecycleForTests();
});

describe('entryPersistLifecycle', () => {
  it('drain is a no-op when nothing is in flight', async () => {
    await expect(drainEntryPersistForSessionChange()).resolves.toBeUndefined();
  });

  it('drain waits for an in-flight persist before resolving', async () => {
    let resolveSave!: () => void;
    const save = new Promise<void>((resolve) => {
      resolveSave = resolve;
    });
    trackEntryPersistInFlight(save);

    let drained = false;
    const drainPromise = drainEntryPersistForSessionChange().then(() => {
      drained = true;
    });

    expect(drained).toBe(false);
    resolveSave();
    await drainPromise;
    expect(drained).toBe(true);
  });

  it('drain swallows persist rejection so session change can proceed', async () => {
    trackEntryPersistInFlight(Promise.reject(new Error('save failed')));
    await expect(drainEntryPersistForSessionChange()).resolves.toBeUndefined();
  });

  it('tracks the latest persist when a newer one is registered', async () => {
    const first = new Promise<void>(() => {
      /* never settles */
    });
    let resolveSecond!: () => void;
    const second = new Promise<void>((resolve) => {
      resolveSecond = resolve;
    });

    trackEntryPersistInFlight(first);
    trackEntryPersistInFlight(second);

    const drained = vi.fn();
    const drainPromise = drainEntryPersistForSessionChange().then(drained);

    // First is still pending; drain should be waiting on second only.
    await Promise.resolve();
    expect(drained).not.toHaveBeenCalled();

    resolveSecond();
    await drainPromise;
    expect(drained).toHaveBeenCalledTimes(1);
  });
});
