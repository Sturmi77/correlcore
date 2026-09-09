<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { WorkContextSummaryItem } from '$lib/api/dashboard';
  import {
    buildWorkContextHeatmapRows,
    nextWorkContextSort,
    sortWorkContextHeatmapRows,
    WORK_CONTEXT_METRICS,
    type WorkContextMetricKey,
    type WorkContextSort,
    type WorkContextSortColumn,
  } from '$lib/utils/homeWorkContextSummary';
  import TrendDirectionGlyph from './TrendDirectionGlyph.svelte';

  export let workContextSummary: WorkContextSummaryItem[] = [];
  export let loading = false;
  export let trendWindowDays = 28;

  const METRIC_LABEL_KEY: Record<WorkContextMetricKey, string> = {
    mood: 'home.brief.metric_mood',
    energy: 'home.brief.metric_energy',
    stress: 'home.brief.metric_stress',
  };

  /** Active sort, or `null` for the default best-situation-first order. */
  let sort: WorkContextSort | null = null;

  function toggleSort(column: WorkContextSortColumn): void {
    sort = nextWorkContextSort(sort, column);
  }

  function columnLabel(column: WorkContextSortColumn): string {
    return column === 'work_context'
      ? $_('home.brief.work_context_column_situation')
      : $_(METRIC_LABEL_KEY[column]);
  }

  // `current` is passed in explicitly so Svelte tracks `sort` as a reactive
  // dependency of every header expression that calls these helpers.
  function ariaSortFor(
    column: WorkContextSortColumn,
    current: WorkContextSort | null
  ): 'ascending' | 'descending' | 'none' {
    if (!current || current.column !== column) return 'none';
    return current.direction === 'asc' ? 'ascending' : 'descending';
  }

  function sortIndicator(column: WorkContextSortColumn, current: WorkContextSort | null): string {
    const state = ariaSortFor(column, current);
    if (state === 'ascending') return '▲';
    if (state === 'descending') return '▼';
    return '↕';
  }

  function sortButtonLabel(column: WorkContextSortColumn, current: WorkContextSort | null): string {
    const state = ariaSortFor(column, current);
    if (state === 'ascending') {
      return $_('home.brief.work_context_sort_ascending', {
        values: { column: columnLabel(column) },
      });
    }
    if (state === 'descending') {
      return $_('home.brief.work_context_sort_descending', {
        values: { column: columnLabel(column) },
      });
    }
    return $_('home.brief.work_context_sort_action', { values: { column: columnLabel(column) } });
  }

  const METRIC_COLOR: Record<WorkContextMetricKey, string> = {
    mood: 'var(--color-metric-mood)',
    energy: 'var(--color-metric-energy)',
    stress: 'var(--color-metric-stress)',
  };

  function formatAverage(value: number | null): string {
    return value === null ? $_('home.brief.none') : value.toFixed(1);
  }

  function trendPhrase(direction: 'up' | 'down' | 'flat' | null): string {
    if (!direction) return '';
    return $_(`home.brief.work_context_trend_${direction}`, {
      values: { n: trendWindowDays },
    });
  }

  $: rows = sortWorkContextHeatmapRows(
    buildWorkContextHeatmapRows(workContextSummary),
    sort,
    (workContext) => $_(`entry.work_context.${workContext}`)
  );
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
      <span>{$_('home.brief.work_context_hint_window', { values: { n: trendWindowDays } })}</span>
    </div>

    <div
      class="work-context-summary__grid"
      data-testid="home-work-context-heatmap"
      role="table"
      aria-label={$_('home.brief.work_context_heading')}
    >
      <div class="work-context-summary__head" role="row">
        <span
          class="work-context-summary__corner"
          role="columnheader"
          aria-sort={ariaSortFor('work_context', sort)}
        >
          <button
            type="button"
            class="work-context-summary__sort"
            data-column="work_context"
            aria-label={sortButtonLabel('work_context', sort)}
            on:click={() => toggleSort('work_context')}
          >
            {$_('home.brief.work_context_column_situation')}
            <span class="work-context-summary__sort-indicator" aria-hidden="true"
              >{sortIndicator('work_context', sort)}</span
            >
          </button>
        </span>
        {#each WORK_CONTEXT_METRICS as metric}
          <span
            class="work-context-summary__col"
            role="columnheader"
            aria-sort={ariaSortFor(metric, sort)}
          >
            <button
              type="button"
              class="work-context-summary__sort"
              data-column={metric}
              aria-label={sortButtonLabel(metric, sort)}
              on:click={() => toggleSort(metric)}
            >
              <i class="work-context-summary__dot" style={`--dot: ${METRIC_COLOR[metric]}`}></i>
              {$_(METRIC_LABEL_KEY[metric])}
              <span class="work-context-summary__sort-indicator" aria-hidden="true"
                >{sortIndicator(metric, sort)}</span
              >
            </button>
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
              data-trend={cell.trendDirection ?? 'none'}
              aria-label={$_('home.brief.work_context_cell', {
                values: {
                  context: $_(`entry.work_context.${row.work_context}`),
                  metric: $_(METRIC_LABEL_KEY[cell.metric]),
                  value: formatAverage(cell.avg),
                  trend: trendPhrase(cell.trendDirection),
                },
              })}
            >
              <span class="work-context-summary__value">
                {cell.avg === null ? '–' : formatAverage(cell.avg)}
              </span>
              {#if cell.trendDirection}
                <span class="work-context-summary__trend" aria-hidden="true">
                  <TrendDirectionGlyph direction={cell.trendDirection} />
                </span>
              {/if}
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

  .work-context-summary__corner {
    display: inline-flex;
    align-items: center;
  }

  .work-context-summary__sort {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-1);
    width: 100%;
    min-height: 1.75rem;
    padding: 0.15rem 0.25rem;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: var(--text-xs);
    font-weight: 600;
    text-align: inherit;
    cursor: pointer;
  }

  .work-context-summary__corner .work-context-summary__sort {
    justify-content: flex-start;
    color: var(--color-text-muted);
  }

  .work-context-summary__sort:hover {
    background: var(--color-surface-dynamic);
  }

  .work-context-summary__sort:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .work-context-summary__sort-indicator {
    flex: 0 0 auto;
    font-size: 0.65rem;
    line-height: 1;
    color: var(--color-text-faint);
  }

  .work-context-summary__col[aria-sort='ascending'] .work-context-summary__sort-indicator,
  .work-context-summary__col[aria-sort='descending'] .work-context-summary__sort-indicator,
  .work-context-summary__corner[aria-sort='ascending'] .work-context-summary__sort-indicator,
  .work-context-summary__corner[aria-sort='descending'] .work-context-summary__sort-indicator {
    color: var(--color-text);
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
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.15rem;
    min-height: 2rem;
    border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-faint);
    background: var(--color-surface-dynamic);
    white-space: nowrap;
  }

  .work-context-summary__trend {
    display: inline-flex;
    flex: 0 0 auto;
    color: var(--color-text-muted);
    width: 0.65rem;
    height: 0.65rem;
  }

  .work-context-summary__trend :global(svg) {
    width: 0.65rem;
    height: 0.65rem;
  }

  .work-context-summary__value {
    display: inline-grid;
    place-items: center;
    min-width: 1.75rem;
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-sm);
    background: color-mix(in oklch, var(--color-surface) 88%, transparent);
    color: var(--color-text);
  }

  /*
   * #854: full sequential heatmap token ladder (same as ComparisonHeatmap /
   * TagHeatmap) so low vs high goodness is perceptually wide. Value chips keep
   * text contrast — intentionally no red/green.
   */
  .work-context-summary__cell--1 {
    background: var(--color-heatmap-1);
  }

  .work-context-summary__cell--2 {
    background: var(--color-heatmap-2);
  }

  .work-context-summary__cell--3 {
    background: var(--color-heatmap-3);
  }

  .work-context-summary__cell--4 {
    background: var(--color-heatmap-4);
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
