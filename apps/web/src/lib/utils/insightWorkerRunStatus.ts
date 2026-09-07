/**
 * Compact copy helpers for Home last-insight-worker status (badge + brief).
 */

import type { InsightWorkerRunSummary } from '$lib/api/insights';

export type TranslateFn = (
  key: string,
  options?: { values?: Record<string, string | number> }
) => string;

/** Format finished_at for the Home strip (relative when recent). */
export function formatInsightRunWhen(
  finishedAt: string | null | undefined,
  _: TranslateFn,
  now: Date = new Date(),
  locale = 'en'
): string | null {
  if (!finishedAt) return null;
  const finished = new Date(finishedAt);
  if (Number.isNaN(finished.getTime())) return null;

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfFinished = new Date(finished.getFullYear(), finished.getMonth(), finished.getDate());
  const dayDiff = Math.round((startOfToday.getTime() - startOfFinished.getTime()) / 86_400_000);
  const time = finished.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });

  if (dayDiff === 0) return _('home.worker_run.when_today', { values: { time } });
  if (dayDiff === 1) return _('home.worker_run.when_yesterday', { values: { time } });
  if (dayDiff > 1 && dayDiff < 7) {
    const weekday = finished.toLocaleDateString(locale, { weekday: 'short' });
    return _('home.worker_run.when_weekday', { values: { weekday, time } });
  }
  const date = finished.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
  return _('home.worker_run.when_date', { values: { date } });
}

/** Compact badge text for HomeTodayContext (under the date). */
export function formatInsightWorkerRunBadge(
  run: InsightWorkerRunSummary | null | undefined,
  _: TranslateFn,
  options: { now?: Date; locale?: string } = {}
): { text: string; tone: 'success' | 'warning' } | null {
  if (!run || run.status === 'never_run' || !run.finished_at) return null;

  const when = formatInsightRunWhen(run.finished_at, _, options.now, options.locale ?? 'en');
  if (!when) return null;

  if (run.status === 'failed') {
    return {
      tone: 'warning',
      text: _('home.worker_run.badge_failed', { values: { when } }),
    };
  }

  if (typeof run.insight_count === 'number') {
    return {
      tone: 'success',
      text: _('home.worker_run.badge_succeeded_with_count', {
        values: { when, count: run.insight_count },
      }),
    };
  }

  return {
    tone: 'success',
    text: _('home.worker_run.badge_succeeded', { values: { when } }),
  };
}

/** One-line status (kept for tests / non-badge surfaces). */
export function formatInsightWorkerRunStatus(
  run: InsightWorkerRunSummary | null | undefined,
  _: TranslateFn,
  options: { now?: Date; locale?: string } = {}
): string | null {
  const badge = formatInsightWorkerRunBadge(run, _, options);
  return badge?.text ?? null;
}
