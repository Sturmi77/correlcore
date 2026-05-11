import type { TimeseriesPoint } from '$lib/api/stats';

export type MetricKey = 'mood_avg' | 'energy_avg' | 'stress_avg';
export type TimeseriesRange = 'week' | 'month' | 'year';
export type PointShape = 'circle' | 'diamond' | 'triangle';

export interface ChartPoint {
  x: number;
  y: number;
  value: number;
  label: string;
}

export interface MetricStyle {
  color: string;
  dasharray: string;
  shape: PointShape;
}

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
    const value = usable[index];
    if (value === null) return [];
    const x = points.length > 1 ? index * step : width / 2;
    const y = height - ((value - 1) / 4) * height;
    return [{ x, y, value, label: point.period_start }];
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
