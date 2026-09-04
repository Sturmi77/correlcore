import type { WorkContextSummaryItem } from '$lib/api/dashboard';
import { heatmapLevel } from '$lib/utils/charts';
import { displayMetricValue } from '$lib/utils/metrics';

/** Metrics shown per work context, in column order. */
export const WORK_CONTEXT_METRICS = ['mood', 'energy', 'stress'] as const;
export type WorkContextMetricKey = (typeof WORK_CONTEXT_METRICS)[number];

const METRIC_SCALE_MAX = 5;

const METRIC_FIELD: Record<WorkContextMetricKey, keyof WorkContextSummaryItem> = {
  mood: 'mood_avg',
  energy: 'energy_avg',
  stress: 'stress_avg',
};

/** Raw average for a metric, or null when unavailable. */
export function workContextMetricAvg(
  item: WorkContextSummaryItem,
  metric: WorkContextMetricKey
): number | null {
  const value = item[METRIC_FIELD[metric]];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/**
 * Normalised "goodness" on the 1–5 scale where higher is always better.
 * Stress is inverted (via `displayMetricValue`) so that stronger heatmap
 * shading consistently reads as "better" across all three columns.
 */
export function workContextMetricGoodness(
  item: WorkContextSummaryItem,
  metric: WorkContextMetricKey
): number | null {
  const raw = workContextMetricAvg(item, metric);
  if (raw === null) return null;
  return metric === 'stress' ? displayMetricValue('stress', raw) : raw;
}

/** Heatmap intensity bucket 0–4 for a goodness value (0 = no data). */
export function workContextGoodnessLevel(goodness: number | null): number {
  if (goodness === null) return 0;
  return heatmapLevel(goodness, METRIC_SCALE_MAX);
}

export interface WorkContextHeatmapCell {
  metric: WorkContextMetricKey;
  /** Raw average for the metric (shown in the cell). */
  avg: number | null;
  /** Normalised 1–5 goodness (stress inverted). */
  goodness: number | null;
  /** Heatmap intensity bucket 0–4. */
  level: number;
}

export interface WorkContextHeatmapRow {
  work_context: WorkContextSummaryItem['work_context'];
  entry_count: number;
  cells: WorkContextHeatmapCell[];
  /** Mean goodness across available metrics — drives row ordering. */
  score: number | null;
}

/**
 * Build heatmap rows (one per work context) with all three metrics as
 * colour-coded cells, sorted best-situation-first by mean goodness.
 */
export function buildWorkContextHeatmapRows(
  items: WorkContextSummaryItem[],
  limit = 6
): WorkContextHeatmapRow[] {
  return items
    .filter((item) => item.entry_count > 0)
    .map((item) => {
      const cells: WorkContextHeatmapCell[] = WORK_CONTEXT_METRICS.map((metric) => {
        const avg = workContextMetricAvg(item, metric);
        const goodness = workContextMetricGoodness(item, metric);
        return { metric, avg, goodness, level: workContextGoodnessLevel(goodness) };
      });
      const goodnessValues = cells
        .map((cell) => cell.goodness)
        .filter((value): value is number => value !== null);
      const score = goodnessValues.length
        ? goodnessValues.reduce((sum, value) => sum + value, 0) / goodnessValues.length
        : null;
      return { work_context: item.work_context, entry_count: item.entry_count, cells, score };
    })
    .filter((row) => row.cells.some((cell) => cell.avg !== null))
    .sort((a, b) => {
      const scoreA = a.score ?? Number.NEGATIVE_INFINITY;
      const scoreB = b.score ?? Number.NEGATIVE_INFINITY;
      if (scoreB !== scoreA) return scoreB - scoreA;
      if (b.entry_count !== a.entry_count) return b.entry_count - a.entry_count;
      return a.work_context.localeCompare(b.work_context);
    })
    .slice(0, limit);
}
