/**
 * Phase 13 / Phase 4 — map changepoint insights to Compare event markers.
 * Neutral “level shift” framing; not used by the Belastung overlay.
 */

import type { InsightResponse } from '$lib/api/insights';
import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function isChangepointInsight(insight: InsightResponse): boolean {
  return (
    insight.insight_type === 'changepoint' ||
    insight.metric === 'mood_changepoint' ||
    insight.metric === 'stress_changepoint' ||
    insight.metric === 'energy_changepoint'
  );
}

export type ChangepointSeries = 'mood_score' | 'stress' | 'energy';

export function changepointSeries(insight: InsightResponse): ChangepointSeries | null {
  const fromPayload = asString(insight.payload?.series);
  if (fromPayload === 'mood_score' || fromPayload === 'stress' || fromPayload === 'energy') {
    return fromPayload;
  }
  if (insight.metric === 'mood_changepoint') return 'mood_score';
  if (insight.metric === 'stress_changepoint') return 'stress';
  if (insight.metric === 'energy_changepoint') return 'energy';
  return null;
}

/** Localized Layer-1 statement from payload (avoids raw English backend string). */
export function formatChangepointStatement(
  insight: InsightResponse,
  t: (key: string, opts?: { values?: Record<string, unknown> }) => string
): string | null {
  if (!isChangepointInsight(insight)) return null;
  const payload = insight.payload ?? {};
  const date = asString(payload.changepoint_date) ?? insight.subject_label;
  const shiftDate = asString(payload.shift_date);
  const before = asNumber(payload.before_avg);
  const after = asNumber(payload.after_avg);
  const series = changepointSeries(insight);
  if (!date || before == null || after == null || !series) return null;
  const direction = after >= before ? 'higher' : 'lower';
  return t('insights.changepoint.statement', {
    values: {
      series: t(`insights.changepoint.series_${series}`),
      date,
      shiftDate: shiftDate ?? date,
      before: before.toFixed(1),
      after: after.toFixed(1),
      direction: t(`insights.changepoint.direction_${direction}`),
    },
  });
}

export function changepointInsightsToMarkers(
  insights: readonly InsightResponse[],
  t: (key: string, opts?: { values?: Record<string, unknown> }) => string,
  options: { axisStart?: string; axisEnd?: string } = {}
): EventMarker[] {
  const { axisStart, axisEnd } = options;
  const markers: EventMarker[] = [];
  for (const insight of insights) {
    if (!isChangepointInsight(insight)) continue;
    const payload = insight.payload ?? {};
    let date = asString(payload.shift_date) ?? asString(payload.changepoint_date);
    if (!date) continue;
    const series = changepointSeries(insight);
    const before = asNumber(payload.before_avg);
    const after = asNumber(payload.after_avg);

    // Phase 4: markers outside the visible window stay as edge markers.
    let clamped = date;
    if (axisStart && date < axisStart) clamped = axisStart;
    if (axisEnd && date > axisEnd) clamped = axisEnd;

    markers.push({
      date: clamped,
      kind: 'phase_transition',
      label: t('insights.changepoint.marker_label', {
        values: {
          series: series
            ? t(`insights.changepoint.series_${series}`)
            : t('insights.changepoint.series_mood_score'),
        },
      }),
      description:
        before != null && after != null
          ? t('insights.changepoint.marker_description', {
              values: { before: before.toFixed(1), after: after.toFixed(1), date },
            })
          : undefined,
    });
  }
  return markers;
}
