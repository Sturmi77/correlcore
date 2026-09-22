import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { createTrendWindowPreference } from './trendWindowPreference';
import type { TrendWindowDays } from '$lib/utils/trendWindowDays';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

async function tickQueue(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe('trend window preference', () => {
  it('serializes rapid 14 → 28 → 90 choices and saves the latest value', async () => {
    const first = deferred<TrendWindowDays>();
    const second = deferred<TrendWindowDays>();
    const write = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const apply = vi.fn();
    const controller = createTrendWindowPreference(write, apply);
    controller.bind('user-1');
    controller.hydrate('user-1', 28, controller.revision());

    controller.select('user-1', 14);
    controller.select('user-1', 28);
    controller.select('user-1', 90);
    expect(write).toHaveBeenCalledTimes(1);
    first.resolve(14);
    await tickQueue();
    expect(write).toHaveBeenCalledTimes(2);
    expect(write.mock.calls[1]?.[0]).toBe(90);
    second.resolve(90);
    await tickQueue();
    expect(apply).toHaveBeenLastCalledWith(90, 'server');
    expect(get({ subscribe: controller.subscribe })).toBe('idle');
  });

  it('shows failure, restores the confirmed value, and retries the failed choice', async () => {
    const write = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(14);
    const apply = vi.fn();
    const controller = createTrendWindowPreference(write, apply);
    controller.bind('user-1');
    controller.hydrate('user-1', 28, controller.revision());
    controller.select('user-1', 14);
    await tickQueue();
    expect(get({ subscribe: controller.subscribe })).toBe('error');
    expect(apply).toHaveBeenLastCalledWith(28, 'server');
    controller.retry();
    await tickQueue();
    expect(write).toHaveBeenCalledTimes(2);
    expect(apply).toHaveBeenLastCalledWith(14, 'server');
  });

  it('ignores a stale hydration and the previous user response', async () => {
    const previous = deferred<TrendWindowDays>();
    const current = deferred<TrendWindowDays>();
    const write = vi
      .fn()
      .mockReturnValueOnce(previous.promise)
      .mockReturnValueOnce(current.promise);
    const apply = vi.fn();
    const controller = createTrendWindowPreference(write, apply);
    controller.bind('user-1');
    const oldRevision = controller.revision();
    controller.select('user-1', 14);
    controller.hydrate('user-1', 28, oldRevision);
    controller.bind('user-2');
    controller.select('user-2', 90);
    previous.resolve(14);
    await tickQueue();
    current.resolve(90);
    await tickQueue();
    expect(apply).toHaveBeenLastCalledWith(90, 'server');
  });
});
