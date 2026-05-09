/**
 * Tests for the auto-save state machine (ADR-0013).
 *
 * The controller is wholly synchronous timer logic + a save-promise,
 * so we drive it with `vi.useFakeTimers()` and a mock save function.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

import { createAutoSave, type AutoSaveState } from './autoSave';

interface Snap {
  v: number;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

function makeController(
  // eslint-disable-next-line no-unused-vars
  saveImpl: (s: Snap) => Promise<void>,
  initialV = 0
) {
  let v = initialV;
  const controller = createAutoSave<Snap>({
    getSnapshot: () => ({ v }),
    save: saveImpl,
    debounceMs: 800,
    savedDisplayMs: 5000,
  });
  return {
    controller,
    setV(next: number) {
      v = next;
      controller.markDirty();
    },
  };
}

function status(c: ReturnType<typeof createAutoSave<Snap>>): AutoSaveState['status'] {
  return get(c.state).status;
}

describe('createAutoSave — initial state', () => {
  it('starts in idle with no error and no last-saved timestamp', () => {
    const c = createAutoSave<Snap>({
      getSnapshot: () => ({ v: 0 }),
      save: vi.fn().mockResolvedValue(undefined),
    });
    const s = get(c.state);
    expect(s.status).toBe('idle');
    expect(s.lastSavedAt).toBeNull();
    expect(s.lastError).toBeNull();
  });
});

describe('createAutoSave — debounce window', () => {
  it('does not fire save before 800 ms have elapsed', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    expect(status(controller)).toBe('dirty');
    await vi.advanceTimersByTimeAsync(700);
    expect(save).not.toHaveBeenCalled();
    expect(status(controller)).toBe('dirty');
  });

  it('fires save exactly once after the debounce window', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith({ v: 1 });
    expect(status(controller)).toBe('saved');
  });

  it('coalesces multiple rapid edits into a single save', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(200);
    setV(2);
    await vi.advanceTimersByTimeAsync(200);
    setV(3);
    await vi.advanceTimersByTimeAsync(800);

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith({ v: 3 });
    expect(status(controller)).toBe('saved');
  });
});

describe('createAutoSave — saved badge fade', () => {
  it('reverts to idle after the savedDisplayMs window', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);
    expect(status(controller)).toBe('saved');

    await vi.advanceTimersByTimeAsync(5000);
    expect(status(controller)).toBe('idle');
  });

  it('records lastSavedAt on success', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);

    expect(get(controller.state).lastSavedAt).not.toBeNull();
    expect(typeof get(controller.state).lastSavedAt).toBe('number');
  });
});

describe('createAutoSave — re-flush during in-flight save', () => {
  it('queues a buffered dirty mark while saving and re-flushes after success', async () => {
    let resolveFirst: () => void = () => {};
    const save = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<void>((resolve) => {
            resolveFirst = resolve;
          })
      )
      .mockResolvedValueOnce(undefined);

    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);
    // First save is in-flight (still pending).
    expect(save).toHaveBeenCalledTimes(1);
    expect(status(controller)).toBe('saving');

    // User edits while we're saving — buffered, status stays `saving`.
    setV(2);
    expect(status(controller)).toBe('saving');
    expect(save).toHaveBeenCalledTimes(1);

    // Now the first save completes; controller should re-enter dirty
    // and schedule the next debounced save.
    resolveFirst();
    await vi.advanceTimersByTimeAsync(0);
    expect(status(controller)).toBe('dirty');

    await vi.advanceTimersByTimeAsync(800);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenLastCalledWith({ v: 2 });
  });
});

describe('createAutoSave — error path', () => {
  it('transitions to error and exposes lastError on save rejection', async () => {
    const save = vi.fn().mockRejectedValue(new Error('boom'));
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);

    const s = get(controller.state);
    expect(s.status).toBe('error');
    expect(s.lastError).toBe('boom');
  });

  it('retry() re-runs the save with the current snapshot', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);
    expect(status(controller)).toBe('error');

    await controller.retry();
    expect(save).toHaveBeenCalledTimes(2);
    expect(status(controller)).toBe('saved');
  });

  it('markDirty after error transitions back to dirty and re-saves', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    await vi.advanceTimersByTimeAsync(800);
    expect(status(controller)).toBe('error');

    setV(2);
    expect(status(controller)).toBe('dirty');
    await vi.advanceTimersByTimeAsync(800);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save).toHaveBeenLastCalledWith({ v: 2 });
    expect(status(controller)).toBe('saved');
  });
});

describe('createAutoSave — flushNow', () => {
  it('saves immediately without waiting for debounce', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    expect(save).not.toHaveBeenCalled();

    await controller.flushNow();
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith({ v: 1 });
  });

  it('is a no-op when state is idle', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const c = createAutoSave<Snap>({ getSnapshot: () => ({ v: 0 }), save });

    await c.flushNow();
    expect(save).not.toHaveBeenCalled();
  });
});

describe('createAutoSave — reset', () => {
  it('cancels a pending debounced save', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    setV(1);
    expect(status(controller)).toBe('dirty');

    controller.reset();
    await vi.advanceTimersByTimeAsync(2000);
    expect(save).not.toHaveBeenCalled();
    expect(status(controller)).toBe('idle');
  });
});

describe('createAutoSave — destroy', () => {
  it('blocks state mutations after destroy', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { controller, setV } = makeController(save);

    controller.destroy();
    setV(1);
    await vi.advanceTimersByTimeAsync(2000);
    // Still idle: destroy short-circuits markDirty and save callbacks.
    expect(save).not.toHaveBeenCalled();
    expect(status(controller)).toBe('idle');
  });
});
