import type { DailyAxisLayout } from '$lib/utils/charts';

/** Shared day-column sizing for Trends compare chart + heatmap (#214 finding 4). */
export const TRENDS_DAY_CELL_REM = 0.82;
export const TRENDS_DAY_GAP_REM = 0.18;
export const TRENDS_LABEL_MIN_REM = 7;
export const TRENDS_AXIS_RIGHT_PADDING_REM = 0;

export interface TrendsDayAxisMetrics {
  rootPx: number;
  labelPx: number;
  cellPx: number;
  gapPx: number;
  rightPaddingPx: number;
}

export function trendsDayAxisMetrics(
  rootPx = 16,
  dayCellRem = TRENDS_DAY_CELL_REM,
  dayGapRem = TRENDS_DAY_GAP_REM
): TrendsDayAxisMetrics {
  return {
    rootPx,
    labelPx: TRENDS_LABEL_MIN_REM * rootPx,
    cellPx: dayCellRem * rootPx,
    gapPx: dayGapRem * rootPx,
    rightPaddingPx: TRENDS_AXIS_RIGHT_PADDING_REM * rootPx,
  };
}

/** Bridge rem-based metrics into the ADR-0035 daily axis layout contract. */
export function toDailyAxisLayout(metrics: TrendsDayAxisMetrics): DailyAxisLayout {
  return {
    labelWidth: metrics.labelPx,
    dayWidth: metrics.cellPx,
    dayGap: metrics.gapPx,
    rightPadding: metrics.rightPaddingPx,
  };
}

export function compareDailyAxisLayoutFromRoot(rootPx = 16): DailyAxisLayout {
  return toDailyAxisLayout(trendsDayAxisMetrics(rootPx));
}

/** X center of a day column (for tests and optional direct SVG use). */
export function trendsDayCenterX(index: number, metrics: TrendsDayAxisMetrics): number {
  return metrics.labelPx + index * (metrics.cellPx + metrics.gapPx) + metrics.cellPx / 2;
}

/** Total plot width for N day columns (excludes trailing padding). */
export function trendsPlotWidth(dayCount: number, metrics: TrendsDayAxisMetrics): number {
  if (dayCount <= 0) return metrics.labelPx;
  return metrics.labelPx + dayCount * metrics.cellPx + (dayCount - 1) * metrics.gapPx;
}

/**
 * Clamp the shared compare axis to the extent of days that actually carry data
 * (#676, follow-up to #629).
 *
 * The compare tab always loads a fixed 365-day window, so the raw axis bounds
 * derived from that window can reach far past the user's first or last logged
 * day. That left an empty scroll region on either side — no hard "Anschlag".
 * This trims the range to ``[max(rawStart, firstDataDate), min(rawEnd,
 * lastDataDate)]`` so the timeline stops at the data on both ends and only spans
 * as far as data exists.
 *
 * ``dataDates`` are the ISO days that hold data (in practice: days with at least
 * one entry — every tag/symptom/work-context layer derives from entries, so the
 * entry-day extent bounds them all). ISO ``YYYY-MM-DD`` strings order
 * chronologically under lexical comparison, so no Date parsing is needed. With
 * no data dates the raw window is returned unchanged.
 */
export function clampAxisRangeToData(
  rawStart: string,
  rawEnd: string,
  dataDates: readonly string[]
): { start: string; end: string } {
  if (dataDates.length === 0) return { start: rawStart, end: rawEnd };
  let first = dataDates[0];
  let last = dataDates[0];
  for (const date of dataDates) {
    if (date < first) first = date;
    if (date > last) last = date;
  }
  const start = rawStart && rawStart > first ? rawStart : first;
  const end = rawEnd && rawEnd < last ? rawEnd : last;
  // If the raw window sits entirely outside the data extent the clamp can invert
  // (start > end); fall back to the data extent so the axis is never empty.
  return start <= end ? { start, end } : { start: first, end: last };
}
