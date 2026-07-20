import type { TimeseriesPoint } from '$lib/api/stats';
import { displayTimeseriesValue } from '$lib/utils/metrics';

export type MetricKey = 'mood_avg' | 'energy_avg' | 'stress_avg';
export type TimeseriesRange = 'week' | 'month' | 'quarter' | 'year';
export type PointShape = 'circle' | 'diamond' | 'triangle';

export interface ChartPoint {
  x: number;
  y: number;
  value: number;
  label: string;
}

export interface DailyAxisLayout {
  labelWidth: number;
  dayWidth: number;
  dayGap: number;
  rightPadding: number;
}

export interface MetricStyle {
  color: string;
  dasharray: string;
  shape: PointShape;
}

export const compareDailyAxisLayout: DailyAxisLayout = {
  labelWidth: 160,
  dayWidth: 18,
  dayGap: 4,
  rightPadding: 18,
};

export const metricStyles: Record<MetricKey, MetricStyle> = {
  mood_avg: {
    color: 'var(--color-metric-mood)',
    dasharray: '',
    shape: 'circle',
  },
  energy_avg: {
    color: 'var(--color-metric-energy)',
    dasharray: '8 5',
    shape: 'diamond',
  },
  stress_avg: {
    color: 'var(--color-metric-stress)',
    dasharray: '2 5',
    shape: 'triangle',
  },
};

export function formatTimeseriesTick(range: TimeseriesRange, isoDate: string): string {
  const [year, month, day] = isoDate.split('-');
  if (!year || !month || !day) return isoDate;
  if (range === 'year') return `${year}-${month}`;
  return `${month}-${day}`;
}

export function buildLinePoints(
  points: readonly TimeseriesPoint[],
  metric: MetricKey,
  width: number,
  height: number
): ChartPoint[] {
  const usable = points.map((point) => point[metric]);
  const step = points.length > 1 ? width / (points.length - 1) : width;
  return points.flatMap((point, index) => {
    const raw = usable[index];
    if (raw === null) return [];
    const value = displayTimeseriesValue(metric, raw);
    const x = points.length > 1 ? index * step : width / 2;
    const y = height - ((value - 1) / 4) * height;
    return [{ x, y, value, label: point.period_start }];
  });
}

export function buildIsoDateRange(start: string, end: string, maxDays = 370): string[] {
  if (!start || !end || start > end) return [];
  const out: string[] = [];
  let cursor = start;
  while (cursor <= end && out.length < maxDays) {
    out.push(cursor);
    const next = shiftIsoDateForAxis(cursor, 1);
    if (next === cursor) break;
    cursor = next;
  }
  return out;
}

function shiftIsoDateForAxis(iso: string, deltaDays: number): string {
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  d.setDate(d.getDate() + deltaDays);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function dailyAxisContentWidth(
  dates: readonly string[],
  layout: Pick<DailyAxisLayout, 'dayWidth' | 'dayGap'> = compareDailyAxisLayout
): number {
  if (dates.length === 0) return 0;
  return dates.length * layout.dayWidth + Math.max(0, dates.length - 1) * layout.dayGap;
}

export function dailyAxisChartWidth(
  dates: readonly string[],
  layout: DailyAxisLayout = compareDailyAxisLayout
): number {
  return (
    layout.labelWidth + layout.dayGap + dailyAxisContentWidth(dates, layout) + layout.rightPadding
  );
}

export function dailyPlotXForIndex(
  index: number,
  layout: Pick<DailyAxisLayout, 'dayWidth' | 'dayGap'> = compareDailyAxisLayout
): number {
  return index * (layout.dayWidth + layout.dayGap) + layout.dayWidth / 2;
}

export function dailyPlotContentWidth(
  dates: readonly string[],
  layout: Pick<DailyAxisLayout, 'dayWidth' | 'dayGap' | 'rightPadding'> = compareDailyAxisLayout
): number {
  return dailyAxisContentWidth(dates, layout) + layout.rightPadding;
}

export function dailyAxisXForIndex(
  index: number,
  layout: Pick<DailyAxisLayout, 'labelWidth' | 'dayWidth' | 'dayGap'> = compareDailyAxisLayout
): number {
  return layout.labelWidth + layout.dayGap + dailyPlotXForIndex(index, layout);
}

export function dailyAxisXForDate(
  date: string,
  dates: readonly string[],
  layout: Pick<DailyAxisLayout, 'labelWidth' | 'dayWidth' | 'dayGap'> = compareDailyAxisLayout
): number | null {
  const index = dates.indexOf(date);
  return index === -1 ? null : dailyAxisXForIndex(index, layout);
}

export function buildDailyAxisLinePoints(
  points: readonly TimeseriesPoint[],
  metric: MetricKey,
  dates: readonly string[],
  height: number,
  layout: Pick<DailyAxisLayout, 'labelWidth' | 'dayWidth' | 'dayGap'> = compareDailyAxisLayout
): ChartPoint[] {
  const byDate = new Map(points.map((point) => [point.period_start, point]));
  return dates.flatMap((date, index) => {
    const point = byDate.get(date);
    if (!point) return [];
    const raw = point[metric];
    if (raw === null) return [];
    const value = displayTimeseriesValue(metric, raw);
    const x = dailyAxisXForIndex(index, layout);
    const y = height - ((value - 1) / 4) * height;
    return [{ x, y, value, label: point.period_start }];
  });
}

export function smoothTimeseriesPoints(
  points: readonly TimeseriesPoint[],
  windowSize = 7
): TimeseriesPoint[] {
  return points.map((point, index) => {
    const window = points.slice(Math.max(0, index - windowSize + 1), index + 1);
    const average = (metric: MetricKey): number | null => {
      // Keep calendar gaps empty so smoothed points stay date-aligned with
      // heatmap activity (no carry-forward onto days without a value).
      if (point[metric] === null) return null;
      const values = window
        .map((item) => item[metric])
        .filter((value): value is number => value !== null);
      if (values.length === 0) return null;
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    };
    return {
      ...point,
      mood_avg: average('mood_avg'),
      energy_avg: average('energy_avg'),
      stress_avg: average('stress_avg'),
    };
  });
}

export function linePath(points: readonly ChartPoint[]): string {
  if (points.length === 0) return '';
  return points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ');
}

export function heatmapLevel(count: number, max: number): number {
  if (count <= 0 || max <= 0) return 0;
  const ratio = count / max;
  if (ratio <= 0.25) return 1;
  if (ratio <= 0.5) return 2;
  if (ratio <= 0.75) return 3;
  return 4;
}
