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

function formatLocaleNumber(value: number, locale: string, fractionDigits: number): string {
  try {
    return value.toLocaleString(locale, {
      minimumFractionDigits: 0,
      maximumFractionDigits: fractionDigits,
    });
  } catch {
    return value.toFixed(fractionDigits);
  }
}

/**
 * Human-readable worker-run duration derived from `finished_at - started_at`.
 *
 * Returns `null` when either timestamp is missing/unparseable or the run is
 * still in progress (no `finished_at`) — callers decide how to render that
 * (hide, or a "running…" label). Sub-second runs show milliseconds, short
 * runs seconds (one decimal below 10 s), longer runs minutes/hours.
 */
export function formatRunDuration(
  startedAt: string | null | undefined,
  finishedAt: string | null | undefined,
  _: TranslateFn,
  locale = 'en'
): string | null {
  if (!startedAt || !finishedAt) return null;
  const start = new Date(startedAt).getTime();
  const end = new Date(finishedAt).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null;

  const ms = end - start;
  if (ms < 1000) {
    return _('home.worker_run.duration_ms', { values: { ms: Math.round(ms) } });
  }

  const totalSeconds = ms / 1000;
  if (totalSeconds < 60) {
    const seconds = formatLocaleNumber(totalSeconds, locale, totalSeconds < 10 ? 1 : 0);
    return _('home.worker_run.duration_seconds', { values: { seconds } });
  }

  const totalMinutes = Math.floor(totalSeconds / 60);
  if (totalMinutes < 60) {
    return _('home.worker_run.duration_minutes', {
      values: { minutes: totalMinutes, seconds: Math.round(totalSeconds % 60) },
    });
  }

  return _('home.worker_run.duration_hours', {
    values: { hours: Math.floor(totalMinutes / 60), minutes: totalMinutes % 60 },
  });
}

/** Compact badge text for HomeTodayContext (under the date). */
export function formatInsightWorkerRunBadge(
  run: InsightWorkerRunSummary | null | undefined,
  _: TranslateFn,
  options: { now?: Date; locale?: string } = {}
): { text: string; tone: 'success' | 'warning' } | null {
  if (!run || run.status === 'never_run' || !run.finished_at) return null;

  const locale = options.locale ?? 'en';
  const when = formatInsightRunWhen(run.finished_at, _, options.now, locale);
  if (!when) return null;

  const duration = formatRunDuration(run.started_at, run.finished_at, _, locale);
  const withDuration = (text: string): string =>
    duration
      ? _('home.worker_run.badge_with_duration', { values: { base: text, duration } })
      : text;

  if (run.status === 'failed') {
    return {
      tone: 'warning',
      text: withDuration(_('home.worker_run.badge_failed', { values: { when } })),
    };
  }

  if (typeof run.insight_count === 'number') {
    return {
      tone: 'success',
      text: withDuration(
        _('home.worker_run.badge_succeeded_with_count', {
          values: { when, count: run.insight_count },
        })
      ),
    };
  }

  return {
    tone: 'success',
    text: withDuration(_('home.worker_run.badge_succeeded', { values: { when } })),
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
