import { describe, expect, it } from 'vitest';
import type { InsightWorkerRunSummary } from '$lib/api/insights';
import {
  formatInsightRunWhen,
  formatInsightWorkerRunBadge,
  formatInsightWorkerRunStatus,
  formatRunDuration,
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

  it('includes insight count on success (no duration when a timestamp is missing)', () => {
    const run: InsightWorkerRunSummary = {
      status: 'succeeded',
      finished_at: '2026-09-07T03:00:00Z',
      started_at: null,
      insight_count: 12,
      trigger_source: 'scheduled',
      generated_for_date: '2026-09-07',
    };
    const badge = formatInsightWorkerRunBadge(run, t, { now, locale: 'en-US' });
    expect(badge?.tone).toBe('success');
    expect(badge?.text).toContain('badge_succeeded_with_count');
    expect(badge?.text).toContain('"count":12');
    // No started_at → duration is omitted, badge is not wrapped.
    expect(badge?.text).not.toContain('badge_with_duration');
  });

  it('appends the run duration when both timestamps are present', () => {
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
    // 02:55 → 03:00 = 5 minutes, wrapped via badge_with_duration.
    expect(badge?.text).toContain('badge_with_duration');
    expect(badge?.text).toContain('badge_succeeded_with_count');
    expect(badge?.text).toContain('duration_minutes');
  });

  it('formats failed runs with warning tone (duration still shown)', () => {
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
    expect(badge?.text).toContain('duration_minutes');
  });
});

describe('formatRunDuration', () => {
  it('returns null when a timestamp is missing or the run is still in flight', () => {
    expect(formatRunDuration(null, '2026-09-07T03:00:00Z', t)).toBeNull();
    expect(formatRunDuration('2026-09-07T03:00:00Z', null, t)).toBeNull();
    expect(formatRunDuration(undefined, undefined, t)).toBeNull();
  });

  it('returns null for a negative or unparseable range', () => {
    expect(formatRunDuration('2026-09-07T03:00:05Z', '2026-09-07T03:00:00Z', t)).toBeNull();
    expect(formatRunDuration('not-a-date', '2026-09-07T03:00:00Z', t)).toBeNull();
  });

  it('formats sub-second runs in milliseconds', () => {
    const result = formatRunDuration('2026-09-07T03:00:00.000Z', '2026-09-07T03:00:00.420Z', t);
    expect(result).toContain('duration_ms');
    expect(result).toContain('"ms":420');
  });

  it('formats short runs in seconds with one decimal below 10s', () => {
    const result = formatRunDuration(
      '2026-09-07T03:00:00.000Z',
      '2026-09-07T03:00:04.200Z',
      t,
      'en-US'
    );
    expect(result).toContain('duration_seconds');
    expect(result).toContain('4.2');
  });

  it('formats multi-minute runs in minutes and seconds', () => {
    const result = formatRunDuration('2026-09-07T02:55:00Z', '2026-09-07T03:00:30Z', t);
    expect(result).toContain('duration_minutes');
    expect(result).toContain('"minutes":5');
    expect(result).toContain('"seconds":30');
  });

  it('formats hour-long runs in hours and minutes', () => {
    const result = formatRunDuration('2026-09-07T01:00:00Z', '2026-09-07T03:30:00Z', t);
    expect(result).toContain('duration_hours');
    expect(result).toContain('"hours":2');
    expect(result).toContain('"minutes":30');
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
