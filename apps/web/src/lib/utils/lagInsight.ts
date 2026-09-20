/**
 * Phase 14 / L8 — parse lag insights for Layer-2 (signal detail) and cards.
 * “Zeitversatz” = signed lag correlation; not Compare Lag-1 “Abfolge”.
 */

import type { InsightResponse } from '$lib/api/insights';

/**
 * One column of the lag profile. `r` is null when that lag carries no
 * measurement at all (too few paired observations, or a constant series) —
 * which is not the same statement as a measured correlation of zero and must
 * not be drawn as one.
 */
export type LagProfileBar = { lag: number; r: number | null; active: boolean };

export type LagFrequencyView = {
  highN: number;
  highGood: number;
  lowN: number;
  lowGood: number;
  goodThreshold: number;
  /** '<=' on stress (lower raw is better), '>=' on mood/energy. */
  goodDirection: 'lte' | 'gte';
  lagDays: number;
  featureKey: string | null;
  featureLabel: string | null;
  targetLabel: string | null;
};

const LAG_PROFILE_MAX_DAYS = 7;

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

export function isLagInsight(insight: InsightResponse): boolean {
  return (
    insight.payload?.method === 'lag' ||
    (insight.insight_type === 'symptom_cluster' && insight.flags?.method === 'lag')
  );
}

/** Same-calendar-day sleep↔mood Spearman — must not share Zeitversatz branding (D4). */
export function isSameDaySleepSpearman(insight: InsightResponse): boolean {
  return insight.metric === 'mood_sleep_minutes' || insight.metric === 'mood_sleep_quality';
}

export function lagProfileBars(insight: InsightResponse): LagProfileBar[] | null {
  if (!isLagInsight(insight)) return null;
  const payload = insight.payload ?? {};
  const raw = payload.lag_profile;
  if (!Array.isArray(raw) || raw.length < 2) return null;
  const chosen = asNumber(payload.lag_days);
  const byLag = new Map<number, number>();
  for (const point of raw) {
    if (
      point &&
      typeof point === 'object' &&
      typeof (point as { lag?: unknown }).lag === 'number' &&
      typeof (point as { r?: unknown }).r === 'number'
    ) {
      byLag.set((point as { lag: number }).lag, (point as { r: number }).r);
    }
  }
  if (byLag.size < 2) return null;
  const bars: LagProfileBar[] = [];
  for (let lag = 1; lag <= LAG_PROFILE_MAX_DAYS; lag += 1) {
    // Absent lag → null, never 0. The backend only emits lags it could actually
    // measure; filling the gaps with zeros would render "not enough data" and
    // "no association" as the same bar.
    bars.push({
      lag,
      r: byLag.has(lag) ? (byLag.get(lag) as number) : null,
      active: lag === chosen,
    });
  }
  return bars;
}

export function parseLagFrequencyView(insight: InsightResponse): LagFrequencyView | null {
  if (!isLagInsight(insight)) return null;
  const payload = insight.payload ?? {};
  const highN = asNumber(payload.high_feature_n);
  const lowN = asNumber(payload.low_feature_n);
  const highGood = asNumber(payload.high_feature_good_count);
  const lowGood = asNumber(payload.low_feature_good_count);
  const lagDays = asNumber(payload.lag_days);
  if (
    highN == null ||
    lowN == null ||
    highGood == null ||
    lowGood == null ||
    lagDays == null ||
    highN <= 0 ||
    lowN <= 0
  ) {
    return null;
  }
  const feature =
    payload.feature && typeof payload.feature === 'object'
      ? (payload.feature as Record<string, unknown>)
      : null;
  const target =
    payload.target && typeof payload.target === 'object'
      ? (payload.target as Record<string, unknown>)
      : null;
  return {
    highN,
    highGood,
    lowN,
    lowGood,
    goodThreshold: asNumber(payload.good_threshold) ?? 4,
    goodDirection: payload.good_direction === 'lte' ? 'lte' : 'gte',
    lagDays,
    featureKey: asString(feature?.key) ?? asString(feature?.slug),
    featureLabel: asString(feature?.name) ?? asString(feature?.label),
    targetLabel: asString(target?.name) ?? asString(target?.label) ?? insight.subject_label,
  };
}
