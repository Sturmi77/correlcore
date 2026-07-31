<script lang="ts">
  /**
   * LagCorrelationHeatmap — #488 Phase 2 (ADR-0035)
   *
   * A pair × lag overview: one row per lag insight (feature → target), columns
   * for lags 1..7, cells encoded by correlation via the shared divergent
   * adapter (midpoint 0, range 2 → r in [-1, 1]). No hue is hardcoded. Fed by
   * the `lag_profile` the backend emits (Phase 1b); self-hides below 2 rows.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { StripCellMapper } from '$lib/charts/adapter';
  import {
    buildLagHeatmapRows,
    LAG_HEATMAP_MAX_DAYS,
    type LagHeatmapRow,
  } from '$lib/utils/lagHeatmap';

  export let insights: InsightResponse[] = [];

  const mapper = new StripCellMapper({ midpoint: 0, range: 2 });
  const lags = Array.from({ length: LAG_HEATMAP_MAX_DAYS }, (_v, i) => i + 1);

  /** Translate core-metric identifiers (mood_score, energy, …) to display names. */
  function metricToken(value: string): string | null {
    if (value === 'mood' || value === 'mood_score') return 'trends.metric.mood';
    if (value === 'energy' || value === 'energy_avg') return 'trends.metric.energy';
    if (value === 'stress' || value === 'stress_avg') return 'trends.metric.stress';
    return null;
  }

  function sideLabel(name: string, key: string | null, kind: string | null): string {
    if (kind === 'metric') {
      const token = metricToken(key ?? name);
      if (token) return $_(token);
    }
    return name;
  }

  function rowLabel(row: LagHeatmapRow): string {
    const feature = sideLabel(row.featureName, row.featureKey, row.featureKind);
    const target = sideLabel(row.targetName, row.targetKey, row.targetKind);
    return `${feature} → ${target}`;
  }

  $: rows = buildLagHeatmapRows(insights).map((row) => ({ ...row, label: rowLabel(row) }));

  // Screen readers treat role="img" as atomic, so the accessible name must
  // carry the data — summarise each pair's strongest lag alongside the layout.
  $: gridSummary = rows
    .map((row) => {
      const best = row.cells
        .filter((cell) => cell.r !== null)
        .reduce<(typeof row.cells)[number] | null>(
          (acc, cell) => (acc && Math.abs(acc.r ?? 0) >= Math.abs(cell.r ?? 0) ? acc : cell),
          null
        );
      return best
        ? $_('insights.lag_heatmap.row_summary', {
            values: { pair: row.label, lag: best.lag, r: (best.r ?? 0).toFixed(2) },
          })
        : row.label;
    })
    .join('; ');
  $: gridAria = `${$_('insights.lag_heatmap.aria')}. ${gridSummary}`;

  // Legend gradient is derived from the same adapter, so it always matches cells.
  $: legendGradient = `linear-gradient(to right, ${mapper.encode(-1).color}, ${
    mapper.encode(0).color
  }, ${mapper.encode(1).color})`;

  function cellStyle(r: number | null): string {
    const encoded = mapper.encode(r ?? Number.NaN);
    return `background: ${encoded.color}; opacity: ${encoded.opacity};`;
  }
</script>

{#if rows.length >= 2}
  <section class="lag-heatmap" data-testid="lag-correlation-heatmap">
    <header class="lag-heatmap__head">
      <h3 class="lag-heatmap__title">{$_('insights.lag_heatmap.title')}</h3>
      <p class="lag-heatmap__subtitle">{$_('insights.lag_heatmap.subtitle')}</p>
    </header>

    <div
      class="lag-heatmap__grid"
      style={`grid-template-columns: minmax(96px, 1.4fr) repeat(${LAG_HEATMAP_MAX_DAYS}, minmax(0, 1fr))`}
      role="img"
      aria-label={gridAria}
    >
      <div class="lag-heatmap__corner" aria-hidden="true"></div>
      {#each lags as lag (lag)}
        <div class="lag-heatmap__col-head" aria-hidden="true">+{lag}</div>
      {/each}

      {#each rows as row (row.id)}
        <div class="lag-heatmap__row-label" aria-hidden="true" title={row.label}>{row.label}</div>
        {#each row.cells as cell (cell.lag)}
          <div
            class="lag-heatmap__cell"
            class:lag-heatmap__cell--active={cell.active}
            class:lag-heatmap__cell--empty={cell.r === null}
            data-lag={cell.lag}
            aria-hidden="true"
            style={cellStyle(cell.r)}
            title={cell.r === null ? `+${cell.lag}d` : `+${cell.lag}d · r=${cell.r.toFixed(2)}`}
          ></div>
        {/each}
      {/each}
    </div>

    <p class="lag-heatmap__legend">
      <span>{$_('insights.lag_heatmap.legend_neg')}</span>
      <span class="lag-heatmap__legend-scale" style={`background: ${legendGradient}`}></span>
      <span>{$_('insights.lag_heatmap.legend_pos')}</span>
    </p>
  </section>
{/if}

<style>
  /* Token-only colour (ADR-0035 §10). Cell fills come from the adapter. */
  .lag-heatmap {
    display: flex;
    flex-direction: column;
    gap: var(--space-2, 0.5rem);
  }

  .lag-heatmap__head {
    display: flex;
    flex-direction: column;
    gap: var(--space-1, 0.25rem);
  }

  .lag-heatmap__title {
    margin: 0;
    font-size: var(--text-md, 1rem);
    color: var(--color-fg);
  }

  .lag-heatmap__subtitle {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-text-muted);
  }

  .lag-heatmap__grid {
    display: grid;
    /* grid-template-columns is set inline from LAG_HEATMAP_MAX_DAYS. */
    gap: 3px;
    align-items: stretch;
    overflow-x: auto;
  }

  .lag-heatmap__corner {
    min-height: 1.25rem;
  }

  .lag-heatmap__col-head {
    text-align: center;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }

  .lag-heatmap__row-label {
    display: flex;
    align-items: center;
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-fg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: var(--space-2, 0.5rem);
  }

  .lag-heatmap__cell {
    aspect-ratio: 1 / 1;
    min-height: 22px;
    border-radius: var(--radius-xs, 2px);
    border: 1px solid transparent;
  }

  .lag-heatmap__cell--empty {
    background: var(--color-strip-track-bg) !important;
    opacity: 1 !important;
  }

  .lag-heatmap__cell--active {
    border-color: var(--color-cursor);
  }

  .lag-heatmap__legend {
    display: flex;
    align-items: center;
    gap: var(--space-2, 0.5rem);
    margin: 0;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }

  .lag-heatmap__legend-scale {
    flex: 1 1 auto;
    height: 8px;
    border-radius: var(--radius-xs, 2px);
    max-width: 160px;
  }
</style>
