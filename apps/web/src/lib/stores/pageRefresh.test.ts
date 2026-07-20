import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { pageRefresh, registerPageRefresh, runRegisteredPageRefresh } from './pageRefresh';

describe('pageRefresh', () => {
  it('registers and clears a handler', () => {
    const handler = vi.fn();
    const unregister = registerPageRefresh(handler);
    expect(get(pageRefresh).hasHandler).toBe(true);
    unregister();
    expect(get(pageRefresh).hasHandler).toBe(false);
  });

  it('runs the registered handler and toggles refreshing', async () => {
    let resolveRefresh!: () => void;
    const handler = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveRefresh = resolve;
        })
    );
    const unregister = registerPageRefresh(handler);

    const pending = runRegisteredPageRefresh();
    expect(get(pageRefresh).refreshing).toBe(true);
    expect(handler).toHaveBeenCalledOnce();

    resolveRefresh();
    await expect(pending).resolves.toBe(true);
    expect(get(pageRefresh).refreshing).toBe(false);

    unregister();
  });

  it('ignores concurrent refresh while one is in flight', async () => {
    let resolveRefresh!: () => void;
    const handler = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveRefresh = resolve;
        })
    );
    const unregister = registerPageRefresh(handler);

    const first = runRegisteredPageRefresh();
    const second = runRegisteredPageRefresh();
    expect(handler).toHaveBeenCalledOnce();
    await expect(second).resolves.toBe(false);

    resolveRefresh();
    await expect(first).resolves.toBe(true);
    unregister();
  });

  it('returns false when no handler is registered', async () => {
    await expect(runRegisteredPageRefresh()).resolves.toBe(false);
  });

  it('does not clear a newer handler when an older unregister runs', () => {
    const first = vi.fn();
    const second = vi.fn();
    const unregisterFirst = registerPageRefresh(first);
    const unregisterSecond = registerPageRefresh(second);
    unregisterFirst();
    expect(get(pageRefresh).hasHandler).toBe(true);
    unregisterSecond();
    expect(get(pageRefresh).hasHandler).toBe(false);
  });
});
