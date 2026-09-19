/**
 * Phase 12 / L5 — same-situation frequencies from insight payload (Layer 2 only).
 * Never frame as "cleaned" / "bereinigt"; speak in natural frequencies.
 */

import type { InsightResponse } from '$lib/api/insights';

export type SameSituationView = {
  context: string;
  withN: number;
  withoutN: number;
  withGood: number;
  withoutGood: number;
  effectSurvives: boolean | null;
  weekdayHeldCoefficient: number | null;
  calendarHeldCoefficient: number | null;
};

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

export function parseSameSituationView(insight: InsightResponse): SameSituationView | null {
  const payload = insight.payload ?? {};
  const context = asString(payload.same_work_context);
  const withN = asNumber(payload.same_work_context_with_n);
  const withoutN = asNumber(payload.same_work_context_without_n);
  const withGood = asNumber(payload.same_work_context_with_good);
  const withoutGood = asNumber(payload.same_work_context_without_good);
  if (
    context == null ||
    withN == null ||
    withoutN == null ||
    withGood == null ||
    withoutGood == null ||
    withN <= 0 ||
    withoutN <= 0
  ) {
    return null;
  }

  const survivesRaw = payload.situation_effect_survives;
  const effectSurvives = typeof survivesRaw === 'boolean' ? survivesRaw : null;

  return {
    context,
    withN,
    withoutN,
    withGood,
    withoutGood,
    effectSurvives,
    weekdayHeldCoefficient: asNumber(payload.weekday_held_coefficient),
    calendarHeldCoefficient: asNumber(payload.calendar_held_coefficient),
  };
}
