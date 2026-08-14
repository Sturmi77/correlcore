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
    const failed = Promise.reject(new Error('save failed'));
    // Attach a no-op catch before tracking so the synthetic reject is not an
    // unhandled rejection in this unit test (production saves are awaited by
    // autoSave and/or drain).
    void failed.catch(() => {});
    trackEntryPersistInFlight(failed);
    await expect(drainEntryPersistForSessionChange()).resolves.toBeUndefined();
  });

  it('drain waits for every overlapping persist, not just the latest', async () => {
    // Regression: a single-slot registry forgot the older persist and let it
    // settle after the session drain. EntrySheet remounts can overlap two saves.
    let resolveFirst!: () => void;
    const first = new Promise<void>((resolve) => {
      resolveFirst = resolve;
    });
    let resolveSecond!: () => void;
    const second = new Promise<void>((resolve) => {
      resolveSecond = resolve;
    });

    trackEntryPersistInFlight(first);
    trackEntryPersistInFlight(second);

    const drained = vi.fn();
    const drainPromise = drainEntryPersistForSessionChange().then(drained);

    // Newest settles first, but the older one is still pending: drain must wait.
    resolveSecond();
    await Promise.resolve();
    await Promise.resolve();
    expect(drained).not.toHaveBeenCalled();

    resolveFirst();
    await drainPromise;
    expect(drained).toHaveBeenCalledTimes(1);
  });

  it('drain also awaits a persist registered after draining began', async () => {
    // The iterative drain must catch an overlapping save that starts (is
    // registered) while an earlier batch is still being awaited.
    let resolveFirst!: () => void;
    const first = new Promise<void>((resolve) => {
      resolveFirst = resolve;
    });
    trackEntryPersistInFlight(first);

    const drained = vi.fn();
    const drainPromise = drainEntryPersistForSessionChange().then(drained);

    let resolveLate!: () => void;
    const late = new Promise<void>((resolve) => {
      resolveLate = resolve;
    });
    trackEntryPersistInFlight(late);

    resolveFirst();
    await Promise.resolve();
    await Promise.resolve();
    expect(drained).not.toHaveBeenCalled();

    resolveLate();
    await drainPromise;
    expect(drained).toHaveBeenCalledTimes(1);
  });
});
