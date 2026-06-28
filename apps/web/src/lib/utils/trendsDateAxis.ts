import type { DailyAxisLayout } from '$lib/utils/charts';

/** Shared day-column sizing for Trends compare chart + heatmap (#214 finding 4). */
export const TRENDS_DAY_CELL_REM = 0.82;
export const TRENDS_DAY_GAP_REM = 0.18;
export const TRENDS_LABEL_MIN_REM = 7;
export const TRENDS_AXIS_RIGHT_PADDING_REM = 1.125;

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
