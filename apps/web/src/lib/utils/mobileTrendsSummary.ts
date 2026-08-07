import type { SymptomHeatmapResponse, TagHeatmapResponse, TimeseriesPoint } from '$lib/api/stats';
import type { MetricKey } from '$lib/utils/charts';

// Order matters: it is the tie-break priority when deltas are equal, so the
// core three stay ahead of optional sleep quality.
const METRICS: MetricKey[] = ['mood_avg', 'energy_avg', 'stress_avg', 'sleep_quality_avg'];

export type MobileMetricMovement = {
  metric: MetricKey;
  from: number;
  to: number;
  delta: number;
};

export type MobileTagSignal = {
  id: string;
  name: string;
  occurrences: number;
  activeDays: number;
};

export type MobileSymptomSignal = {
  id: string;
  name: string;
  reports: number;
  peakIntensity: number;
};

export type MobileTrendsSummary = {
  entryCount: number;
  movement: MobileMetricMovement | null;
  tag: MobileTagSignal | null;
  symptom: MobileSymptomSignal | null;
};

function metricMovement(points: TimeseriesPoint[]): MobileMetricMovement | null {
  const candidates = METRICS.flatMap((metric) => {
    const values = points
      .map((point) => point[metric])
      .filter((value): value is number => typeof value === 'number');
    if (values.length < 2) return [];
    const from = values[0];
    const to = values[values.length - 1];
    return [{ metric, from, to, delta: to - from }];
  });

  return (
    candidates.sort(
      (left, right) =>
        Math.abs(right.delta) - Math.abs(left.delta) ||
        METRICS.indexOf(left.metric) - METRICS.indexOf(right.metric)
    )[0] ?? null
  );
}

function strongestTag(heatmap: TagHeatmapResponse | null): MobileTagSignal | null {
  if (!heatmap) return null;
  return (
    heatmap.tags
      .map((tag) => ({
        id: tag.tag_id,
        name: tag.name,
        occurrences: tag.days.reduce((total, day) => total + day.count, 0),
        activeDays: tag.days.filter((day) => day.count > 0).length,
      }))
      .filter((tag) => tag.occurrences > 0)
      .sort(
        (left, right) =>
          right.occurrences - left.occurrences ||
          right.activeDays - left.activeDays ||
          left.name.localeCompare(right.name)
      )[0] ?? null
  );
}

function strongestSymptom(heatmap: SymptomHeatmapResponse | null): MobileSymptomSignal | null {
  if (!heatmap) return null;
  return (
    heatmap.symptoms
      .map((symptom) => ({
        id: symptom.symptom_id,
        name: symptom.name,
        reports: symptom.days.reduce((total, day) => total + day.count, 0),
        peakIntensity: symptom.days.reduce((peak, day) => Math.max(peak, day.max_intensity), 0),
      }))
      .filter((symptom) => symptom.reports > 0)
      .sort(
        (left, right) =>
          right.reports - left.reports ||
          right.peakIntensity - left.peakIntensity ||
          left.name.localeCompare(right.name)
      )[0] ?? null
  );
}

export function buildMobileTrendsSummary(
  points: TimeseriesPoint[],
  tagHeatmap: TagHeatmapResponse | null,
  symptomHeatmap: SymptomHeatmapResponse | null
): MobileTrendsSummary {
  const orderedPoints = [...points].sort((left, right) =>
    left.period_start.localeCompare(right.period_start)
  );
  return {
    entryCount: orderedPoints.reduce((total, point) => total + point.entry_count, 0),
    movement: metricMovement(orderedPoints),
    tag: strongestTag(tagHeatmap),
    symptom: strongestSymptom(symptomHeatmap),
  };
}
