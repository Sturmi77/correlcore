<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { WorkContextSummaryItem } from '$lib/api/dashboard';
  import {
    buildWorkContextHeatmapRows,
    WORK_CONTEXT_METRICS,
    type WorkContextMetricKey,
  } from '$lib/utils/homeWorkContextSummary';

  export let workContextSummary: WorkContextSummaryItem[] = [];
  export let loading = false;

  const METRIC_LABEL_KEY: Record<WorkContextMetricKey, string> = {
    mood: 'home.brief.metric_mood',
    energy: 'home.brief.metric_energy',
    stress: 'home.brief.metric_stress',
  };

  const METRIC_COLOR: Record<WorkContextMetricKey, string> = {
    mood: 'var(--color-metric-mood)',
    energy: 'var(--color-metric-energy)',
    stress: 'var(--color-metric-stress)',
  };

  function formatAverage(value: number | null): string {
    return value === null ? $_('home.brief.none') : value.toFixed(1);
  }

  $: rows = buildWorkContextHeatmapRows(workContextSummary);
</script>

{#if rows.length || loading}
  <section
    class="work-context-summary"
    data-testid="home-work-context-summary"
    aria-busy={loading}
    aria-label={$_('home.brief.work_context_heading')}
  >
    <div class="work-context-summary__header">
      <h3>{$_('home.brief.work_context_heading')}</h3>
      <span>{$_('home.brief.work_context_hint')}</span>
    </div>

    <div
      class="work-context-summary__grid"
      data-testid="home-work-context-heatmap"
      role="table"
      aria-label={$_('home.brief.work_context_heading')}
    >
      <div class="work-context-summary__head" role="row">
        <span class="work-context-summary__corner" role="columnheader"></span>
        {#each WORK_CONTEXT_METRICS as metric}
          <span class="work-context-summary__col" role="columnheader">
            <i class="work-context-summary__dot" style={`--dot: ${METRIC_COLOR[metric]}`}></i>
            {$_(METRIC_LABEL_KEY[metric])}
          </span>
        {/each}
      </div>

      {#each rows as row (row.work_context)}
        <div class="work-context-summary__row" role="row" data-context={row.work_context}>
          <span class="work-context-summary__label" role="rowheader">
            {$_(`entry.work_context.${row.work_context}`)}
            <small
              >{$_('home.brief.work_context_days', { values: { count: row.entry_count } })}</small
            >
          </span>
          {#each row.cells as cell}
            <span
              class={`work-context-summary__cell work-context-summary__cell--${cell.level}`}
              role="cell"
              data-metric={cell.metric}
              data-level={cell.level}
              aria-label={$_('home.brief.work_context_cell', {
                values: {
                  context: $_(`entry.work_context.${row.work_context}`),
                  metric: $_(METRIC_LABEL_KEY[cell.metric]),
                  value: formatAverage(cell.avg),
                },
              })}
            >
              {cell.avg === null ? '–' : formatAverage(cell.avg)}
            </span>
          {/each}
        </div>
      {/each}
    </div>

    <div class="work-context-summary__legend" aria-hidden="true">
      <span>{$_('home.brief.work_context_legend_low')}</span>
      <span class="work-context-summary__legend-scale">
        {#each [1, 2, 3, 4] as level}
          <i class={`work-context-summary__cell--${level}`}></i>
        {/each}
      </span>
      <span>{$_('home.brief.work_context_legend_high')}</span>
    </div>
    <p class="work-context-summary__note">{$_('home.brief.work_context_stress_note')}</p>
  </section>
{/if}

<style>
  .work-context-summary {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-5);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .work-context-summary__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: baseline;
  }

  .work-context-summary__header h3 {
    margin: 0;
    font-size: var(--text-sm);
  }

  .work-context-summary__header span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .work-context-summary__grid {
    display: grid;
    gap: var(--space-1);
  }

  .work-context-summary__head,
  .work-context-summary__row {
    display: grid;
    grid-template-columns: minmax(6rem, 1.1fr) repeat(3, minmax(3rem, 1fr));
    gap: var(--space-1);
    align-items: stretch;
  }

  .work-context-summary__col {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-text-muted);
    text-align: center;
  }

  .work-context-summary__dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: var(--radius-full);
    background: var(--dot, var(--color-primary));
    flex: 0 0 auto;
  }

  .work-context-summary__label {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    font-size: var(--text-sm);
    overflow-wrap: anywhere;
  }

  .work-context-summary__label small {
    color: var(--color-text-faint);
    font-size: var(--text-xs);
  }

  .work-context-summary__cell {
    display: grid;
    place-items: center;
    min-height: 2rem;
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-faint);
    background: var(--color-surface-dynamic);
  }

  /*
   * Sequential single-hue ramp built from the project heatmap token
   * (see ComparisonHeatmap). Tinted over the surface so the in-cell value
   * keeps sufficient contrast in both themes — intentionally no red/green.
   */
  .work-context-summary__cell--1 {
    color: var(--color-text);
    background: color-mix(in oklch, var(--color-heatmap-4) 16%, var(--color-surface));
  }

  .work-context-summary__cell--2 {
    color: var(--color-text);
    background: color-mix(in oklch, var(--color-heatmap-4) 30%, var(--color-surface));
  }

  .work-context-summary__cell--3 {
    color: var(--color-text);
    background: color-mix(in oklch, var(--color-heatmap-4) 44%, var(--color-surface));
  }

  .work-context-summary__cell--4 {
    color: var(--color-text);
    background: color-mix(in oklch, var(--color-heatmap-4) 58%, var(--color-surface));
  }

  .work-context-summary__legend {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-text-faint);
  }

  .work-context-summary__legend-scale {
    display: inline-flex;
    gap: 3px;
  }

  .work-context-summary__legend-scale i {
    width: 1.15rem;
    height: 0.55rem;
    border-radius: var(--radius-sm);
  }

  .work-context-summary__note {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-faint);
  }

  @media (max-width: 480px) {
    .work-context-summary__header {
      flex-direction: column;
      gap: var(--space-1);
    }

    .work-context-summary__head,
    .work-context-summary__row {
      grid-template-columns: minmax(4.5rem, 1fr) repeat(3, minmax(2.5rem, 1fr));
    }
  }
</style>
