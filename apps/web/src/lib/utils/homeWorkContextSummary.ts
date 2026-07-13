import type { WorkContextSummaryItem } from '$lib/api/dashboard';
import { displayMetricValue } from '$lib/utils/metrics';

const METRIC_SCALE_MAX = 5;

export type WorkContextMetricKey = 'mood' | 'energy' | 'stress';

const METRIC_FIELD: Record<WorkContextMetricKey, keyof WorkContextSummaryItem> = {
  mood: 'mood_avg',
  energy: 'energy_avg',
  stress: 'stress_avg',
};

const METRIC_INVERT: Record<WorkContextMetricKey, boolean> = {
  mood: false,
  energy: false,
  stress: true,
};

export type WorkContextDisplayItem = WorkContextSummaryItem & {
  /** Deviation from the weighted average for the active metric. */
  metricDelta: number | null;
  /** Raw average for the active metric. */
  metricAvg: number | null;
};

export function workContextMetricAvg(
  item: WorkContextSummaryItem,
  metric: WorkContextMetricKey
): number | null {
  const value = item[METRIC_FIELD[metric]];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function weightedMoodAverage(items: WorkContextSummaryItem[]): number | null {
  return weightedMetricAverage(items, 'mood');
}

export function weightedMetricAverage(
  items: WorkContextSummaryItem[],
  metric: WorkContextMetricKey
): number | null {
  const withMetric = items.filter(
    (item) => workContextMetricAvg(item, metric) !== null && item.entry_count > 0
  );
  if (!withMetric.length) return null;

  const totalWeight = withMetric.reduce((sum, item) => sum + item.entry_count, 0);
  if (totalWeight <= 0) return null;

  const weighted = withMetric.reduce(
    (sum, item) => sum + workContextMetricAvg(item, metric)! * item.entry_count,
    0
  );
  return weighted / totalWeight;
}

export function buildWorkContextDisplayItems(
  items: WorkContextSummaryItem[],
  metric: WorkContextMetricKey = 'mood',
  limit = 4
): WorkContextDisplayItem[] {
  const overall = weightedMetricAverage(items, metric);
  return items
    .filter((item) => item.entry_count > 0 && workContextMetricAvg(item, metric) !== null)
    .map((item) => {
      const metricAvg = workContextMetricAvg(item, metric);
      return {
        ...item,
        metricAvg,
        metricDelta: overall === null || metricAvg === null ? null : metricAvg - overall,
        moodDelta: overall === null || metricAvg === null ? null : metricAvg - overall,
      };
    })
    .sort((a, b) => {
      const deltaA = Math.abs(a.metricDelta ?? 0);
      const deltaB = Math.abs(b.metricDelta ?? 0);
      if (deltaB !== deltaA) return deltaB - deltaA;
      if (b.entry_count !== a.entry_count) return b.entry_count - a.entry_count;
      return a.work_context.localeCompare(b.work_context);
    })
    .slice(0, limit);
}

/** Bar width uses display-normalized values so inverted metrics read consistently. */
export function workContextMetricBarWidth(
  metric: WorkContextMetricKey,
  rawAvg: number | null
): string {
  if (rawAvg === null) return '0%';
  const displayValue =
    metric === 'stress'
      ? displayMetricValue('stress', rawAvg)
      : metric === 'energy'
        ? rawAvg
        : rawAvg;
  const ratio = Math.min(METRIC_SCALE_MAX, Math.max(0, displayValue)) / METRIC_SCALE_MAX;
  return `${ratio * 100}%`;
}

/** @deprecated Use workContextMetricBarWidth */
export function workContextMoodBarWidth(moodAvg: number | null): string {
  return workContextMetricBarWidth('mood', moodAvg);
}

export function workContextMetricHighLow(
  values: readonly number[],
  metric: WorkContextMetricKey
): { high: number | null; low: number | null } {
  if (!values.length) return { high: null, low: null };
  const invert = METRIC_INVERT[metric];
  const high = invert ? Math.min(...values) : Math.max(...values);
  const low = invert ? Math.max(...values) : Math.min(...values);
  if (high === low) return { high: null, low: null };
  return { high, low };
}

export function workContextMetricCssVar(metric: WorkContextMetricKey): string {
  if (metric === 'energy') return 'var(--color-metric-energy)';
  if (metric === 'stress') return 'var(--color-metric-stress)';
  return 'var(--color-metric-mood)';
}

/** Neutral bar fill when a row has no high/low highlight. */
export function workContextMetricNeutralBarColor(metric: WorkContextMetricKey): string {
  // Reserve metric-stress red for the worst context only (see HomeDailyBrief stress CSS).
  if (metric === 'stress') return 'var(--color-primary)';
  return workContextMetricCssVar(metric);
}
