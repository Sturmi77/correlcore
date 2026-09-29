import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import type { InsightResponse } from '$lib/api/insights';
import {
  formatChangepointStatement,
  changepointInsightsToMarkers,
} from '$lib/utils/changepointMarkers';
import fixture from './insightContract.fixture.json';
import SignalScatter from './SignalScatter.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

function translate(key: string, options?: { values?: Record<string, unknown> }): string {
  return `${key}:${JSON.stringify(options?.values ?? {})}`;
}

describe('API → adapter → render contract', () => {
  it('uses the same stress raw and display directions in text, marker and plot', () => {
    const insight = fixture as InsightResponse;
    const statement = formatChangepointStatement(insight, translate) ?? '';
    expect(statement).toContain('direction_higher');
    expect(statement).toContain('"before":"2.0"');
    expect(statement).toContain('"after":"5.0"');
    expect(statement).toContain('"displayBefore":"4.0"');
    expect(statement).toContain('"displayAfter":"1.0"');

    const marker = changepointInsightsToMarkers([insight], translate)[0];
    expect(marker.date).toBe('2026-03-11');
    expect(marker.description).toContain('"before":"4.0"');
    expect(marker.description).toContain('"after":"1.0"');

    const { container } = render(SignalScatter, {
      metric: 'stress',
      points: [
        { date: '2026-03-10', value: fixture.payload.before_avg, present: true },
        { date: '2026-03-11', value: fixture.payload.after_avg, present: true },
      ],
      withMean: 5,
      withoutMean: 2,
      withSe: 0.1,
      withoutSe: 0.1,
    });
    const dots = [...container.querySelectorAll('circle')];
    expect(Number(dots[0].getAttribute('cy'))).toBeLessThan(Number(dots[1].getAttribute('cy')));
  });
});
