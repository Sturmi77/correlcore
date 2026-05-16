/**
 * Insight readiness estimation — Issue #184, FRONTEND.md §6.4.
 *
 * Pure helpers: no API calls. Parents pass distinct day-entry ISO dates
 * (typically from an entries list already loaded for the insights screen).
 */

import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';

export const INSIGHT_READINESS_TARGET = 30;
export const INSIGHT_PACE_WINDOW_DAYS = 14;
export const INSIGHT_FULL_DATA_THRESHOLD = 90;

export type InsightReadinessStage =
  | 'getting_started'
  | 'building_with_pace'
  | 'building_no_recent'
  | 'ready_low'
  | 'ready_full';

export interface InsightReadinessInput {
  /** Distinct ISO dates with at least one `slot=day` entry. */
  dayEntryDates: readonly string[];
  paceWindowDays?: number;
  targetEntries?: number;
  fullDataThreshold?: number;
  /** Reference calendar day (defaults to local today). */
  asOfIso?: string | undefined;
}

export interface InsightReadinessEstimate {
  stage: InsightReadinessStage;
  totalEntryCount: number;
  targetEntries: number;
  /** Distinct day entries in the pace window ending on `asOfIso`. */
  recentEntryCount: number;
  entriesRemaining: number;
  /** Rounded whole weeks; null when pace cannot be estimated. */
  estimatedWeeks: number | null;
  /** Progress toward first insight (0–1), capped at 1. */
  progressRatio: number;
  paceWindowDays: number;
  showProgressFraction: boolean;
}

/** Collect distinct `slot=day` dates from API entries. */
export function dayEntryDatesFromIsoEntries(
  entries: readonly { entry_date: string; slot: string }[]
): string[] {
  const dates = new Set<string>();
  for (const e of entries) {
    if (e.slot === 'day') dates.add(e.entry_date);
  }
  return [...dates].sort();
}

function countDatesInWindow(dates: readonly string[], asOfIso: string, windowDays: number): number {
  const start = shiftIsoDate(asOfIso, -(windowDays - 1));
  const inWindow = new Set<string>();
  for (const d of dates) {
    if (d >= start && d <= asOfIso) inWindow.add(d);
  }
  return inWindow.size;
}

export function estimateInsightReadiness(input: InsightReadinessInput): InsightReadinessEstimate {
  const target = input.targetEntries ?? INSIGHT_READINESS_TARGET;
  const fullThreshold = input.fullDataThreshold ?? INSIGHT_FULL_DATA_THRESHOLD;
  const windowDays = input.paceWindowDays ?? INSIGHT_PACE_WINDOW_DAYS;
  const asOfIso = input.asOfIso ?? localIsoDate(new Date());
  const uniqueDates = [...new Set(input.dayEntryDates)].sort();
  const total = uniqueDates.length;
  const recent = countDatesInWindow(uniqueDates, asOfIso, windowDays);
  const progressRatio = Math.min(1, total / target);
  const entriesRemaining = Math.max(0, target - total);

  if (total <= 3) {
    return {
      stage: 'getting_started',
      totalEntryCount: total,
      targetEntries: target,
      recentEntryCount: recent,
      entriesRemaining,
      estimatedWeeks: null,
      progressRatio,
      paceWindowDays: windowDays,
      showProgressFraction: false,
    };
  }

  if (total < target) {
    if (recent === 0) {
      return {
        stage: 'building_no_recent',
        totalEntryCount: total,
        targetEntries: target,
        recentEntryCount: 0,
        entriesRemaining,
        estimatedWeeks: null,
        progressRatio,
        paceWindowDays: windowDays,
        showProgressFraction: true,
      };
    }

    const entriesPerDay = recent / windowDays;
    const daysUntilTarget =
      entriesPerDay > 0 ? entriesRemaining / entriesPerDay : Number.POSITIVE_INFINITY;
    const estimatedWeeks =
      Number.isFinite(daysUntilTarget) && daysUntilTarget > 0
        ? Math.max(1, Math.ceil(daysUntilTarget / 7))
        : null;

    return {
      stage: 'building_with_pace',
      totalEntryCount: total,
      targetEntries: target,
      recentEntryCount: recent,
      entriesRemaining,
      estimatedWeeks,
      progressRatio,
      paceWindowDays: windowDays,
      showProgressFraction: true,
    };
  }

  if (total < fullThreshold) {
    return {
      stage: 'ready_low',
      totalEntryCount: total,
      targetEntries: target,
      recentEntryCount: recent,
      entriesRemaining: 0,
      estimatedWeeks: null,
      progressRatio: 1,
      paceWindowDays: windowDays,
      showProgressFraction: false,
    };
  }

  return {
    stage: 'ready_full',
    totalEntryCount: total,
    targetEntries: target,
    recentEntryCount: recent,
    entriesRemaining: 0,
    estimatedWeeks: null,
    progressRatio: 1,
    paceWindowDays: windowDays,
    showProgressFraction: false,
  };
}
