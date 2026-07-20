import { render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { registerPageRefresh } from '$lib/stores/pageRefresh';
import PullToRefreshHarness from './PullToRefresh.harness.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
    isLoading: readable(false),
  };
});

function touch(target: Element, type: string, clientY: number): TouchEvent {
  const touchPoint = {
    clientX: 0,
    clientY,
    identifier: 1,
    pageX: 0,
    pageY: clientY,
    screenX: 0,
    screenY: clientY,
    target,
    radiusX: 1,
    radiusY: 1,
    rotationAngle: 0,
    force: 1,
  } as Touch;
  return new TouchEvent(type, {
    bubbles: true,
    cancelable: true,
    touches: type === 'touchend' || type === 'touchcancel' ? [] : [touchPoint],
    changedTouches: [touchPoint],
    targetTouches: type === 'touchend' || type === 'touchcancel' ? [] : [touchPoint],
  });
}

describe('PullToRefresh', () => {
  let unregister: (() => void) | null = null;

  beforeEach(() => {
    unregister?.();
    unregister = null;
  });

  afterEach(() => {
    unregister?.();
    unregister = null;
  });

  it('renders chrome and content', () => {
    render(PullToRefreshHarness);
    expect(screen.getByTestId('pull-to-refresh')).toBeTruthy();
    expect(screen.getByText('content')).toBeTruthy();
  });

  it('runs the registered handler after a full pull gesture', async () => {
    const handler = vi.fn(async () => undefined);
    unregister = registerPageRefresh(handler);

    render(PullToRefreshHarness);
    await tick();

    const scroll = screen.getByTestId('ptr-scroll');
    Object.defineProperty(scroll, 'scrollTop', { configurable: true, get: () => 0 });

    scroll.dispatchEvent(touch(scroll, 'touchstart', 40));
    scroll.dispatchEvent(touch(scroll, 'touchmove', 220));
    scroll.dispatchEvent(touch(scroll, 'touchend', 220));

    await waitFor(() => expect(handler).toHaveBeenCalledOnce());
    await waitFor(() =>
      expect(screen.getByTestId('pull-to-refresh-indicator').getAttribute('aria-busy')).toBe(
        'false'
      )
    );
  });

  it('does not refresh when disabled', async () => {
    const handler = vi.fn(async () => undefined);
    unregister = registerPageRefresh(handler);

    render(PullToRefreshHarness, { props: { disabled: true } });
    await tick();

    const scroll = screen.getByTestId('ptr-scroll');
    Object.defineProperty(scroll, 'scrollTop', { configurable: true, get: () => 0 });

    scroll.dispatchEvent(touch(scroll, 'touchstart', 40));
    scroll.dispatchEvent(touch(scroll, 'touchmove', 220));
    scroll.dispatchEvent(touch(scroll, 'touchend', 220));

    await tick();
    expect(handler).not.toHaveBeenCalled();
  });

  it('ignores gestures that start inside data-ptr-ignore', async () => {
    const handler = vi.fn(async () => undefined);
    unregister = registerPageRefresh(handler);

    render(PullToRefreshHarness, { props: { withIgnoreTarget: true } });
    await tick();

    const scroll = screen.getByTestId('ptr-scroll');
    Object.defineProperty(scroll, 'scrollTop', { configurable: true, get: () => 0 });
    const ignore = screen.getByTestId('ptr-ignore-target');

    ignore.dispatchEvent(touch(ignore, 'touchstart', 40));
    ignore.dispatchEvent(touch(ignore, 'touchmove', 220));
    ignore.dispatchEvent(touch(ignore, 'touchend', 220));

    await tick();
    expect(handler).not.toHaveBeenCalled();
  });
});
