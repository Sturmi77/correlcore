import type { MetricTrend, WorkContextSummaryItem } from '$lib/api/dashboard';
import { heatmapLevel } from '$lib/utils/charts';
import {
  displayMetricAvg,
  visibleTrendDirection,
  type VisibleTrendDirection,
} from '$lib/utils/metricTrend';
import { displayMetricValue } from '$lib/utils/metrics';

/** Metrics shown per work context, in column order. */
export const WORK_CONTEXT_METRICS = ['mood', 'energy', 'stress'] as const;
export type WorkContextMetricKey = (typeof WORK_CONTEXT_METRICS)[number];

const METRIC_SCALE_MAX = 5;

/**
 * Minimum goodness span (on the 1–5 scale) before a column switches from the
 * absolute 1–5 bucket map to a relative stretch across the visible rows (#854).
 * Narrower spans fall back so tiny noise is not amplified into full contrast.
 */
export const WORK_CONTEXT_RELATIVE_MIN_SPAN = 1;

const METRIC_FIELD: Record<WorkContextMetricKey, keyof WorkContextSummaryItem> = {
  mood: 'mood_avg',
  energy: 'energy_avg',
  stress: 'stress_avg',
};

const METRIC_TREND_FIELD: Record<WorkContextMetricKey, keyof WorkContextSummaryItem> = {
  mood: 'mood_trend',
  energy: 'energy_trend',
  stress: 'stress_trend',
};

export interface GoodnessRange {
  min: number;
  max: number;
}

/** Raw average for a metric, or null when unavailable. Prefers the window mean. */
export function workContextMetricAvg(
  item: WorkContextSummaryItem,
  metric: WorkContextMetricKey
): number | null {
  const allTime = item[METRIC_FIELD[metric]];
  const trend = item[METRIC_TREND_FIELD[metric]];
  return displayMetricAvg(
    typeof allTime === 'number' ? allTime : null,
    trend && typeof trend === 'object' && 'direction' in trend ? (trend as MetricTrend) : null
  );
}

export function workContextMetricTrend(
  item: WorkContextSummaryItem,
  metric: WorkContextMetricKey
): VisibleTrendDirection | null {
  const trend = item[METRIC_TREND_FIELD[metric]];
  return visibleTrendDirection(
    trend && typeof trend === 'object' && 'direction' in trend ? (trend as MetricTrend) : null
  );
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

/**
 * Heatmap intensity bucket 0–4 for a goodness value (0 = no data).
 *
 * When `range` spans at least {@link WORK_CONTEXT_RELATIVE_MIN_SPAN}, the value
 * is stretched across that column's observed min…max so low vs high situations
 * use the full 1…4 ramp. Otherwise falls back to the absolute 1–5 scale.
 */
export function workContextGoodnessLevel(
  goodness: number | null,
  range?: GoodnessRange | null
): number {
  if (goodness === null) return 0;

  if (range) {
    const span = range.max - range.min;
    if (span >= WORK_CONTEXT_RELATIVE_MIN_SPAN) {
      const t = (goodness - range.min) / span;
      if (t <= 0.25) return 1;
      if (t <= 0.5) return 2;
      if (t <= 0.75) return 3;
      return 4;
    }
  }

  return heatmapLevel(goodness, METRIC_SCALE_MAX);
}

/** Min/max goodness for one metric across already-filtered rows. */
export function workContextColumnRange(
  rows: ReadonlyArray<{
    cells: ReadonlyArray<{ metric: WorkContextMetricKey; goodness: number | null }>;
  }>,
  metric: WorkContextMetricKey
): GoodnessRange | null {
  const values = rows
    .map((row) => row.cells.find((cell) => cell.metric === metric)?.goodness)
    .filter((value): value is number => value !== null);
  if (!values.length) return null;
  return { min: Math.min(...values), max: Math.max(...values) };
}

export interface WorkContextHeatmapCell {
  metric: WorkContextMetricKey;
  /** Raw average for the metric (shown in the cell). */
  avg: number | null;
  /** Normalised 1–5 goodness (stress inverted). */
  goodness: number | null;
  /** Heatmap intensity bucket 0–4. */
  level: number;
  /** Chip glyph; null when unknown or missing. */
  trendDirection: VisibleTrendDirection | null;
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
 *
 * Colour levels are assigned in a second pass using a **per-column relative**
 * scale over the rows that remain after sort/limit (#854).
 */
export function buildWorkContextHeatmapRows(
  items: WorkContextSummaryItem[],
  limit = 6
): WorkContextHeatmapRow[] {
  const rows = items
    .filter((item) => item.entry_count > 0)
    .map((item) => {
      const cells: WorkContextHeatmapCell[] = WORK_CONTEXT_METRICS.map((metric) => {
        const avg = workContextMetricAvg(item, metric);
        const goodness = workContextMetricGoodness(item, metric);
        return {
          metric,
          avg,
          goodness,
          level: 0,
          trendDirection: workContextMetricTrend(item, metric),
        };
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

  const ranges = Object.fromEntries(
    WORK_CONTEXT_METRICS.map((metric) => [metric, workContextColumnRange(rows, metric)])
  ) as Record<WorkContextMetricKey, GoodnessRange | null>;

  for (const row of rows) {
    for (const cell of row.cells) {
      cell.level = workContextGoodnessLevel(cell.goodness, ranges[cell.metric]);
    }
  }

  return rows;
}

/** Column the heatmap can be sorted by: the situation name or one metric. */
export type WorkContextSortColumn = 'work_context' | WorkContextMetricKey;
export type WorkContextSortDirection = 'asc' | 'desc';

export interface WorkContextSort {
  column: WorkContextSortColumn;
  direction: WorkContextSortDirection;
}

/**
 * Next sort state when a column header is activated.
 *
 * Cycles through the column: first click → ascending, second → descending,
 * third → back to the default order (`null`). Activating a different column
 * starts a fresh ascending sort on it.
 */
export function nextWorkContextSort(
  current: WorkContextSort | null,
  column: WorkContextSortColumn
): WorkContextSort | null {
  if (!current || current.column !== column) return { column, direction: 'asc' };
  if (current.direction === 'asc') return { column, direction: 'desc' };
  return null;
}

function metricAvgOf(row: WorkContextHeatmapRow, metric: WorkContextMetricKey): number | null {
  return row.cells.find((cell) => cell.metric === metric)?.avg ?? null;
}

/**
 * Reorder built heatmap rows by the chosen column and direction.
 *
 * - `null` sort keeps the default best-situation-first order from
 *   {@link buildWorkContextHeatmapRows}.
 * - The `work_context` column sorts by the resolved (localised) label using a
 *   locale-aware comparison; pass `labelFor` to sort by the displayed name.
 * - Metric columns sort by the raw average shown in the cell. Rows without a
 *   value for that metric always sort to the end regardless of direction, and
 *   the situation label breaks ties.
 *
 * Rows are copied, never mutated, so heatmap levels stay valid.
 */
export function sortWorkContextHeatmapRows(
  rows: WorkContextHeatmapRow[],
  sort: WorkContextSort | null,
  labelFor: (workContext: WorkContextHeatmapRow['work_context']) => string = (wc) => wc
): WorkContextHeatmapRow[] {
  if (!sort) return rows;

  const factor = sort.direction === 'asc' ? 1 : -1;
  const byLabel = (a: WorkContextHeatmapRow, b: WorkContextHeatmapRow) =>
    labelFor(a.work_context).localeCompare(labelFor(b.work_context), 'de');

  const sorted = [...rows];

  if (sort.column === 'work_context') {
    sorted.sort((a, b) => factor * byLabel(a, b));
    return sorted;
  }

  const metric = sort.column;
  sorted.sort((a, b) => {
    const av = metricAvgOf(a, metric);
    const bv = metricAvgOf(b, metric);
    if (av === null && bv === null) return byLabel(a, b);
    if (av === null) return 1;
    if (bv === null) return -1;
    if (av !== bv) return factor * (av - bv);
    return byLabel(a, b);
  });
  return sorted;
}
