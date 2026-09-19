/**
 * Changepoint markers for Compare (Phase 4 / L4, #933 payload dates).
 *
 * Maps mood `changepoint` insights onto `phase_transition` EventMarkers and
 * optional segment midlines. Detection stays backend-only; this module is
 * presentation glue.
 */

import type { InsightResponse } from '$lib/api/insights';
import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';
import type { AxisBucket } from '$lib/utils/compareAxisZoom';

export type ChangepointDirection = 'higher' | 'lower';

export type ChangepointSegmentGuide = {
  /** Last day of the before-segment (ISO). */
  changepointDate: string;
  /** First day of the after-segment (ISO). */
  shiftDate: string;
  beforeAvg: number;
  afterAvg: number;
};

export type ChangepointDatePair = {
  index: number;
  changepoint_date: string;
  shift_date: string;
};

export type ParsedChangepointPayload = {
  changepointDate: string;
  shiftDate: string;
  beforeAvg: number;
  afterAvg: number;
  dates: ChangepointDatePair[];
};

function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function asFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** Read the Phase-3 date payload; returns null when dates are missing. */
export function parseChangepointPayload(
  payload: Record<string, unknown> | null | undefined
): ParsedChangepointPayload | null {
  if (!payload) return null;
  const changepointDate = payload.changepoint_date;
  const shiftDate = payload.shift_date;
  const beforeAvg = asFiniteNumber(payload.before_avg);
  const afterAvg = asFiniteNumber(payload.after_avg);
  if (
    !isIsoDate(changepointDate) ||
    !isIsoDate(shiftDate) ||
    beforeAvg === null ||
    afterAvg === null
  ) {
    return null;
  }

  const rawDates = payload.changepoint_dates;
  const dates: ChangepointDatePair[] = [];
  if (Array.isArray(rawDates)) {
    for (const item of rawDates) {
      if (!item || typeof item !== 'object') continue;
      const record = item as Record<string, unknown>;
      if (
        typeof record.index === 'number' &&
        isIsoDate(record.changepoint_date) &&
        isIsoDate(record.shift_date)
      ) {
        dates.push({
          index: record.index,
          changepoint_date: record.changepoint_date,
          shift_date: record.shift_date,
        });
      }
    }
  }
  if (dates.length === 0) {
    dates.push({
      index: typeof payload.changepoint_index === 'number' ? payload.changepoint_index : 0,
      changepoint_date: changepointDate,
      shift_date: shiftDate,
    });
  }

  return { changepointDate, shiftDate, beforeAvg, afterAvg, dates };
}

export function changepointDirection(beforeAvg: number, afterAvg: number): ChangepointDirection {
  return afterAvg >= beforeAvg ? 'higher' : 'lower';
}

/**
 * Localized Ebene-1 sentence from payload (not the English backend statement).
 * `t` is the svelte-i18n `$_` helper.
 */
export function formatChangepointStatement(
  insight: InsightResponse,
  t: (key: string, options?: { values?: Record<string, string | number> }) => string
): string | null {
  if (insight.insight_type !== 'changepoint') return null;
  const parsed = parseChangepointPayload(insight.payload);
  if (!parsed) return null;
  const direction = changepointDirection(parsed.beforeAvg, parsed.afterAvg);
  return t('insights.card.changepoint_statement', {
    values: {
      date: parsed.shiftDate,
      before: parsed.beforeAvg.toFixed(1),
      after: parsed.afterAvg.toFixed(1),
      direction: t(`insights.card.changepoint_direction_${direction}`),
    },
  });
}

/** Prefer localized changepoint copy; otherwise fall back to the raw statement. */
export function resolveInsightStatement(
  insight: InsightResponse,
  t: (key: string, options?: { values?: Record<string, string | number> }) => string,
  fallback: (raw: string | null | undefined) => string
): string {
  return formatChangepointStatement(insight, t) ?? fallback(insight.statement);
}

export type ChangepointMarkerLabels = {
  label: string;
  descriptionFor: (beforeAvg: number, afterAvg: number) => string;
};

/**
 * Build phase_transition markers from latest changepoint insights.
 * Vertical line sits on `shift_date` (first day of the after-segment) — the
 * honest “from …” boundary. Weaker PELT hits from `changepoint_dates` are
 * included without segment midlines.
 */
export function insightsToChangepointMarkers(
  insights: readonly InsightResponse[],
  labels: ChangepointMarkerLabels
): EventMarker[] {
  const markers: EventMarker[] = [];
  const seen = new Set<string>();

  for (const insight of insights) {
    if (insight.insight_type !== 'changepoint') continue;
    const parsed = parseChangepointPayload(insight.payload);
    if (!parsed) continue;

    const primaryDescription = labels.descriptionFor(parsed.beforeAvg, parsed.afterAvg);
    for (const pair of parsed.dates) {
      const date = pair.shift_date;
      if (seen.has(date)) continue;
      seen.add(date);
      const isPrimary = pair.shift_date === parsed.shiftDate;
      markers.push({
        date,
        kind: 'phase_transition',
        label: labels.label,
        ...(isPrimary ? { description: primaryDescription } : {}),
      });
    }
  }

  return markers;
}

export function insightsToChangepointSegments(
  insights: readonly InsightResponse[]
): ChangepointSegmentGuide[] {
  const segments: ChangepointSegmentGuide[] = [];
  for (const insight of insights) {
    if (insight.insight_type !== 'changepoint') continue;
    const parsed = parseChangepointPayload(insight.payload);
    if (!parsed) continue;
    segments.push({
      changepointDate: parsed.changepointDate,
      shiftDate: parsed.shiftDate,
      beforeAvg: parsed.beforeAvg,
      afterAvg: parsed.afterAvg,
    });
  }
  return segments;
}

/**
 * Pin a calendar date onto the visible axis: exact hit, else edge of the
 * window when outside, else nearest key for in-window gaps.
 */
export function pinIsoDateToAxisKeys(date: string, axisKeys: readonly string[]): string | null {
  if (axisKeys.length === 0) return null;
  if (axisKeys.includes(date)) return date;
  const first = axisKeys[0]!;
  const last = axisKeys[axisKeys.length - 1]!;
  if (date < first) return first;
  if (date > last) return last;

  let best = first;
  let bestDist = Infinity;
  const target = Date.parse(date);
  for (const key of axisKeys) {
    const dist = Math.abs(Date.parse(key) - target);
    if (dist < bestDist) {
      bestDist = dist;
      best = key;
    }
  }
  return best;
}

/** Clamp to an inclusive calendar window without requiring the date on a key list. */
export function clampIsoDateToWindow(date: string, windowStart: string, windowEnd: string): string {
  if (date < windowStart) return windowStart;
  if (date > windowEnd) return windowEnd;
  return date;
}

function bucketStartForDateClamped(date: string, buckets: readonly AxisBucket[]): string | null {
  if (buckets.length === 0) return null;
  const hit = buckets.find((bucket) => bucket.dates.includes(date));
  if (hit) return hit.start;

  const firstBucket = buckets[0]!;
  const lastBucket = buckets[buckets.length - 1]!;
  const windowStart = firstBucket.dates[0] ?? firstBucket.start;
  const windowEnd = lastBucket.dates[lastBucket.dates.length - 1] ?? lastBucket.start;
  if (date < windowStart) return firstBucket.start;
  if (date > windowEnd) return lastBucket.start;

  const covering = buckets.find((bucket) => {
    const end = bucket.dates[bucket.dates.length - 1] ?? bucket.start;
    return bucket.start <= date && date <= end;
  });
  return (
    covering?.start ??
    pinIsoDateToAxisKeys(
      date,
      buckets.map((bucket) => bucket.start)
    )
  );
}

/**
 * Remap markers onto display-axis keys (bucket starts when zoomed). Dates
 * outside the window become edge markers instead of disappearing.
 */
export function remapEventMarkersToDisplayAxis(
  markers: readonly EventMarker[],
  axisKeys: readonly string[],
  buckets: readonly AxisBucket[] = []
): EventMarker[] {
  return markers
    .map((marker) => {
      const start =
        buckets.length > 0
          ? bucketStartForDateClamped(marker.date, buckets)
          : pinIsoDateToAxisKeys(marker.date, axisKeys);
      if (!start) return null;
      const endRaw = marker.endDate
        ? buckets.length > 0
          ? bucketStartForDateClamped(marker.endDate, buckets)
          : pinIsoDateToAxisKeys(marker.endDate, axisKeys)
        : undefined;
      return {
        ...marker,
        date: start,
        ...(endRaw && endRaw !== start ? { endDate: endRaw } : { endDate: undefined }),
      };
    })
    .filter((marker): marker is EventMarker => marker !== null);
}

/** Y in plot-local coordinates (0 = top of plot) for a 1–5 score. */
export function scoreToPlotY(score: number, plotHeight: number): number {
  const clamped = Math.min(5, Math.max(1, score));
  return plotHeight - ((clamped - 1) / 4) * plotHeight;
}
