import type { InsightResponse } from '$lib/api/insights';

/** #488 Phase 2: lag-correlation heatmap (pair × lag), built from lag insights. */
export const LAG_HEATMAP_MAX_DAYS = 7;

export interface LagHeatmapCell {
  lag: number;
  /** Correlation at this lag, or null when the lag was not observed for the pair. */
  r: number | null;
  active: boolean;
}

export interface LagHeatmapRow {
  id: string;
  label: string;
  chosenLag: number | null;
  cells: LagHeatmapCell[];
}

function featureName(value: unknown): string | null {
  if (value && typeof value === 'object') {
    const name = (value as { name?: unknown }).name;
    if (typeof name === 'string' && name.length > 0) return name;
  }
  return null;
}

/**
 * Turn the lag insights in a feed into heatmap rows. Each row is one
 * feature→target pair; columns are lags 1..7 with the correlation from the
 * insight's `lag_profile` (Phase 1b). Rows without a usable profile (< 2
 * observed lags) are skipped so the heatmap never shows a single-point "curve".
 */
export function buildLagHeatmapRows(insights: readonly InsightResponse[]): LagHeatmapRow[] {
  const rows: LagHeatmapRow[] = [];
  for (const insight of insights) {
    const payload = insight.payload as Record<string, unknown> | undefined;
    if (!payload || payload.method !== 'lag') continue;
    const raw = payload.lag_profile;
    if (!Array.isArray(raw) || raw.length < 2) continue;

    const byLag = new Map<number, number>();
    for (const point of raw) {
      if (
        point &&
        typeof point === 'object' &&
        typeof (point as { lag?: unknown }).lag === 'number' &&
        typeof (point as { r?: unknown }).r === 'number'
      ) {
        byLag.set((point as { lag: number }).lag, (point as { r: number }).r);
      }
    }
    if (byLag.size < 2) continue;

    const chosenLag = typeof payload.lag_days === 'number' ? payload.lag_days : null;
    const feature = featureName(payload.feature) ?? insight.subject_label ?? 'Feature';
    const target = featureName(payload.target) ?? insight.metric ?? 'Target';
    const cells: LagHeatmapCell[] = [];
    for (let lag = 1; lag <= LAG_HEATMAP_MAX_DAYS; lag += 1) {
      cells.push({
        lag,
        r: byLag.has(lag) ? (byLag.get(lag) ?? null) : null,
        active: lag === chosenLag,
      });
    }
    rows.push({ id: insight.id, label: `${feature} → ${target}`, chosenLag, cells });
  }
  return rows;
}
