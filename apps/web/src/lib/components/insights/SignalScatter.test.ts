import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import SignalScatter from './SignalScatter.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

describe('SignalScatter stress scale', () => {
  it('plots raw 5 below raw 2 and labels the positive display scale', () => {
    const { container } = render(SignalScatter, {
      metric: 'stress',
      points: [
        { date: '2026-01-01', value: 5, present: true },
        { date: '2026-01-02', value: 2, present: false },
      ],
      withMean: 5,
      withoutMean: 2,
      withSe: 0.5,
      withoutSe: 0.5,
    });
    const dots = [...container.querySelectorAll('circle')];
    expect(Number(dots[0].getAttribute('cy'))).toBeGreaterThan(Number(dots[1].getAttribute('cy')));
    const ticks = [...container.querySelectorAll('.scatter__tick')];
    expect(ticks[0].textContent).toBe('5');
    expect(ticks[1].textContent).toBe('1');
    expect(Number(ticks[0].getAttribute('y'))).toBeLessThan(Number(ticks[1].getAttribute('y')));
    expect(
      [...container.querySelectorAll('rect')].every(
        (rect) => Number(rect.getAttribute('height')) > 0
      )
    ).toBe(true);
  });
});
