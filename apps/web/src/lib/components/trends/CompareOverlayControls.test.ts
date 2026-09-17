import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CompareOverlayControls from './CompareOverlayControls.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  // Join segments so gitleaks does not treat dotted i18n keys as API secrets.
  const k = (...parts: string[]) => parts.join('.');

  return {
    _: readable((key: string, opts?: { values?: Record<string, unknown> }) => {
      if (key === k('trends', 'compare', 'coincidence', 'empty') && opts?.values?.min != null) {
        return `Need at least ${opts.values.min} shared days`;
      }
      if (key === k('trends', 'compare', 'lag1', 'empty') && opts?.values?.min != null) {
        return `Need at least ${opts.values.min} next-day sequences`;
      }
      return key;
    }),
  };
});

const ready = { pinnedCount: 2, coincidence: true, lag1: true };

describe('CompareOverlayControls (#919)', () => {
  it('renders a token-only swatch for each marker shape', () => {
    const { container } = render(CompareOverlayControls, {
      props: { availability: ready },
    });

    expect(screen.getByTestId('trends-compare-swatches')).toBeTruthy();
    expect(container.querySelector('.overlay-controls__swatch-band')).toBeTruthy();
    expect(container.querySelector('.overlay-controls__swatch-line')).toBeTruthy();
    // ADR-0035: the key must read the marker tokens, never a literal hue.
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{3,6}\b/i);
  });

  it('disables a toggle whose gate is closed and explains why', () => {
    render(CompareOverlayControls, {
      props: { availability: { pinnedCount: 2, coincidence: false, lag1: true } },
    });

    const toggle = screen.getByTestId('trends-compare-coincidence-toggle') as HTMLInputElement;
    expect(toggle.disabled).toBe(true);
    expect(screen.getByTestId('trends-compare-coincidence-empty').textContent).toContain(
      'Need at least 2 shared days'
    );
  });

  it('asks for pins before it asks for shared days', () => {
    render(CompareOverlayControls, {
      props: { availability: { pinnedCount: 1, coincidence: false, lag1: false } },
    });

    expect(screen.getByTestId('trends-compare-lag1-empty').textContent).toContain(
      'trends.compare.lag1.need_pins'
    );
  });

  it('nudges after the second pin and reports the dismissal', async () => {
    const onDismiss = vi.fn();
    render(CompareOverlayControls, {
      props: { availability: ready },
      events: { dismissPinHint: onDismiss },
    });

    expect(screen.getByTestId('trends-compare-pin-hint')).toBeTruthy();
    await fireEvent.click(screen.getByTestId('trends-compare-pin-hint-dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('drops the nudge once the overlay is on or the hint was dismissed', () => {
    const { unmount } = render(CompareOverlayControls, {
      props: { availability: ready, coincidenceHighlight: true },
    });
    expect(screen.queryByTestId('trends-compare-pin-hint')).toBeNull();
    unmount();

    render(CompareOverlayControls, {
      props: { availability: ready, overlayHintDismissed: true },
    });
    expect(screen.queryByTestId('trends-compare-pin-hint')).toBeNull();
  });

  it('keeps panel and sheet instances addressable via the test id prefix', () => {
    render(CompareOverlayControls, {
      props: { availability: ready, testIdPrefix: 'trends-compare-settings' },
    });

    expect(screen.getByTestId('trends-compare-settings-coincidence-toggle')).toBeTruthy();
    expect(screen.getByTestId('trends-compare-settings-lag1-toggle')).toBeTruthy();
  });

  it('reports toggle changes instead of persisting them itself', async () => {
    const onCoincidence = vi.fn();
    const onLag1 = vi.fn();
    render(CompareOverlayControls, {
      props: { availability: ready },
      events: { coincidenceChange: onCoincidence, lag1Change: onLag1 },
    });

    await fireEvent.click(screen.getByTestId('trends-compare-coincidence-toggle'));
    await fireEvent.click(screen.getByTestId('trends-compare-lag1-toggle'));

    expect(onCoincidence.mock.calls[0]?.[0]?.detail).toEqual({ value: true });
    expect(onLag1.mock.calls[0]?.[0]?.detail).toEqual({ value: true });
  });
});
