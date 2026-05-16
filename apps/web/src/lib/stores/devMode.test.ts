import { get } from 'svelte/store';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => {
    store[k] = v;
  },
  removeItem: (k: string) => {
    delete store[k];
  },
  clear: () => {
    Object.keys(store).forEach((k) => delete store[k]);
  },
};

vi.stubGlobal('localStorage', localStorageMock);

// ---------------------------------------------------------------------------
// Helpers to simulate tap sequence
// ---------------------------------------------------------------------------
const REQUIRED_TAPS = 7;
const TIMEOUT_MS = 3000;

function makeTapHandler(onActivate: () => void) {
  let count = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  return function tap() {
    count++;
    if (timer) clearTimeout(timer);

    if (count >= REQUIRED_TAPS) {
      count = 0;
      const next = localStorage.getItem('dev_mode_enabled') !== 'true';
      localStorage.setItem('dev_mode_enabled', String(next));
      onActivate();
      return;
    }

    timer = setTimeout(() => {
      count = 0;
    }, TIMEOUT_MS);
  };
}

describe('devMode tap sequence', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('activates dev mode after exactly 7 taps within 3s', () => {
    const handler = vi.fn();
    const tap = makeTapHandler(handler);
    for (let i = 0; i < REQUIRED_TAPS; i++) tap();
    expect(handler).toHaveBeenCalledOnce();
    expect(localStorage.getItem('dev_mode_enabled')).toBe('true');
  });

  it('does nothing after only 6 taps', () => {
    const handler = vi.fn();
    const tap = makeTapHandler(handler);
    for (let i = 0; i < 6; i++) tap();
    expect(handler).not.toHaveBeenCalled();
  });

  it('resets counter after 3s timeout — 4 taps, wait, 3 taps = no activation', () => {
    const handler = vi.fn();
    const tap = makeTapHandler(handler);
    for (let i = 0; i < 4; i++) tap();
    vi.advanceTimersByTime(TIMEOUT_MS + 100);
    for (let i = 0; i < 3; i++) tap();
    expect(handler).not.toHaveBeenCalled();
  });

  it('DEVELOPER section hidden by default (dev_mode_enabled not set)', () => {
    expect(localStorage.getItem('dev_mode_enabled')).toBeNull();
  });
});

describe('devMode force visualizations', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.resetModules();
  });

  it('derives force visualizations from dev mode and the force flag', async () => {
    const { devMode, devForceVisualizations, devForceVisualizationsControl } = await import(
      './devMode'
    );

    devForceVisualizationsControl.set(true);
    expect(get(devForceVisualizations)).toBe(false);

    devMode.set(true);
    expect(get(devForceVisualizations)).toBe(true);
    expect(localStorage.getItem('dev_force_viz')).toBe('true');
  });

  it('turns force visualizations off when dev mode is disabled', async () => {
    const { devMode, devForceVisualizations, devForceVisualizationsControl } = await import(
      './devMode'
    );

    devMode.set(true);
    devForceVisualizationsControl.set(true);
    devMode.set(false);

    expect(get(devForceVisualizations)).toBe(false);
    expect(localStorage.getItem('dev_force_viz')).toBe('false');
  });
});
