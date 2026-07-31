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
  /** Raw feature/target metadata — the component composes + translates the label. */
  featureName: string;
  targetName: string;
  featureKind: string | null;
  targetKind: string | null;
  featureKey: string | null;
  targetKey: string | null;
  chosenLag: number | null;
  cells: LagHeatmapCell[];
}

function featureField(value: unknown, field: 'name' | 'key' | 'kind'): string | null {
  if (value && typeof value === 'object') {
    const candidate = (value as Record<string, unknown>)[field];
    if (typeof candidate === 'string' && candidate.length > 0) return candidate;
  }
  return null;
}

/**
 * Turn the lag insights in a feed into heatmap rows. Each row is one
 * feature→target pair; columns are lags 1..7 with the correlation from the
 * insight's `lag_profile` (Phase 1b). Rows without a usable profile (< 2
 * observed lags) are skipped so the heatmap never shows a single-point "curve".
 *
 * run_lag_analysis emits one insight per surviving lag for a pair (and
 * /insights/latest keeps them because lag_days is part of its dedup key), so we
 * collapse to one row per feature→target pair here — those insights share the
 * same profile, and the feed is ordered by |correlation|, so the first is the
 * pair's strongest lag.
 */
export function buildLagHeatmapRows(insights: readonly InsightResponse[]): LagHeatmapRow[] {
  const rows: LagHeatmapRow[] = [];
  const seenPairs = new Set<string>();

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

    const featureName = featureField(payload.feature, 'name') ?? insight.subject_label ?? 'Feature';
    const targetName = featureField(payload.target, 'name') ?? insight.metric ?? 'Target';
    const featureKey = featureField(payload.feature, 'key');
    const targetKey = featureField(payload.target, 'key');

    const pairKey = `${featureKey ?? featureName}→${targetKey ?? targetName}`;
    if (seenPairs.has(pairKey)) continue;
    seenPairs.add(pairKey);

    const chosenLag = typeof payload.lag_days === 'number' ? payload.lag_days : null;
    const cells: LagHeatmapCell[] = [];
    for (let lag = 1; lag <= LAG_HEATMAP_MAX_DAYS; lag += 1) {
      cells.push({
        lag,
        r: byLag.has(lag) ? (byLag.get(lag) ?? null) : null,
        active: lag === chosenLag,
      });
    }

    rows.push({
      id: insight.id,
      featureName,
      targetName,
      featureKind: featureField(payload.feature, 'kind'),
      targetKind: featureField(payload.target, 'kind'),
      featureKey,
      targetKey,
      chosenLag,
      cells,
    });
  }
  return rows;
}
