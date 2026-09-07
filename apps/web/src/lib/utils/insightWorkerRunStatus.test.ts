import { describe, expect, it } from 'vitest';
import type { InsightWorkerRunSummary } from '$lib/api/insights';
import {
  formatInsightRunWhen,
  formatInsightWorkerRunBadge,
  formatInsightWorkerRunStatus,
} from './insightWorkerRunStatus';

const t = (key: string, options?: { values?: Record<string, unknown> }) => {
  const values = options?.values ?? {};
  return `${key}:${JSON.stringify(values)}`;
};

describe('formatInsightRunWhen', () => {
  const now = new Date('2026-09-07T15:00:00Z');

  it('formats today with time', () => {
    const result = formatInsightRunWhen('2026-09-07T03:00:00Z', t, now, 'en-US');
    expect(result).toContain('home.worker_run.when_today');
  });

  it('formats yesterday', () => {
    const result = formatInsightRunWhen('2026-09-06T03:00:00Z', t, now, 'en-US');
    expect(result).toContain('home.worker_run.when_yesterday');
  });
});

describe('formatInsightWorkerRunBadge', () => {
  const now = new Date('2026-09-07T15:00:00Z');

  it('returns null when no run', () => {
    expect(formatInsightWorkerRunBadge(null, t, { now })).toBeNull();
  });

  it('includes insight count on success', () => {
    const run: InsightWorkerRunSummary = {
      status: 'succeeded',
      finished_at: '2026-09-07T03:00:00Z',
      started_at: '2026-09-07T02:55:00Z',
      insight_count: 12,
      trigger_source: 'scheduled',
      generated_for_date: '2026-09-07',
    };
    const badge = formatInsightWorkerRunBadge(run, t, { now, locale: 'en-US' });
    expect(badge?.tone).toBe('success');
    expect(badge?.text).toContain('badge_succeeded_with_count');
    expect(badge?.text).toContain('"count":12');
  });

  it('formats failed runs with warning tone', () => {
    const run: InsightWorkerRunSummary = {
      status: 'failed',
      finished_at: '2026-09-07T03:00:00Z',
      started_at: '2026-09-07T02:55:00Z',
      insight_count: null,
      trigger_source: 'scheduled',
      generated_for_date: null,
    };
    const badge = formatInsightWorkerRunBadge(run, t, { now, locale: 'en-US' });
    expect(badge?.tone).toBe('warning');
    expect(badge?.text).toContain('badge_failed');
  });
});

describe('formatInsightWorkerRunStatus', () => {
  it('delegates to badge text', () => {
    const run: InsightWorkerRunSummary = {
      status: 'succeeded',
      finished_at: '2026-09-07T03:00:00Z',
      started_at: '2026-09-07T02:55:00Z',
      insight_count: 2,
      trigger_source: 'scheduled',
      generated_for_date: '2026-09-07',
    };
    expect(
      formatInsightWorkerRunStatus(run, t, { now: new Date('2026-09-07T15:00:00Z') })
    ).toContain('badge_succeeded_with_count');
  });
});
