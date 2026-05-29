<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
  import { heatmapLevel } from '$lib/utils/charts';
  import { shiftIsoDate } from '$lib/utils/streak';

  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let loading = false;

  const dispatch = createEventDispatcher<{ selectDate: { date: string; rowId: string } }>();

  type Row = {
    id: string;
    label: string;
    kind: 'tag' | 'symptom';
    days: { date: string; count: number; max_intensity?: number }[];
  };

  let scroller: HTMLDivElement;
  let lastKey = '';

  function buildDates(start: string, end: string): string[] {
    const out: string[] = [];
    let cursor = start;
    while (cursor <= end && out.length < 370) {
      out.push(cursor);
      cursor = shiftIsoDate(cursor, 1);
    }
    return out;
  }

  function valueFor(row: Row, date: string): number {
    const day = row.days.find((item) => item.date === date);
    if (!day) return 0;
    return row.kind === 'symptom' ? (day.max_intensity ?? day.count) : day.count;
  }

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (scroller) scroller.scrollLeft = scroller.scrollWidth;
  }

  $: startDate = tagHeatmap?.start_date ?? symptomHeatmap?.start_date ?? '';
  $: endDate = tagHeatmap?.end_date ?? symptomHeatmap?.end_date ?? '';
  $: dates = startDate && endDate ? buildDates(startDate, endDate) : [];
  $: rows = [
    ...(showTags
      ? (tagHeatmap?.tags ?? []).map(
          (tag): Row => ({
            id: tag.tag_id,
            label: tag.name,
            kind: 'tag',
            days: tag.days,
          })
        )
      : []),
    ...(showSymptoms
      ? (symptomHeatmap?.symptoms ?? []).map(
          (symptom): Row => ({
            id: symptom.symptom_id,
            label: symptom.name,
            kind: 'symptom',
            days: symptom.days,
          })
        )
      : []),
  ];
  $: maxValue = Math.max(0, ...rows.flatMap((row) => dates.map((date) => valueFor(row, date))));
  $: scrollKey = `${startDate}:${endDate}:${rows.length}`;
  $: if (scrollKey && scrollKey !== lastKey) {
    lastKey = scrollKey;
    void scrollToLatest();
  }
</script>

<section class="compare-heatmap" data-loading={loading ? 'true' : 'false'}>
  <header class="compare-heatmap__head">
    <h3>{$_('trends.compare.heatmap_heading')}</h3>
    {#if startDate && endDate}
      <span>{startDate} - {endDate}</span>
    {/if}
  </header>

  {#if loading && rows.length === 0}
    <div class="compare-heatmap__empty" role="status">{$_('trends.compare.loading')}</div>
  {:else if rows.length > 0}
    <div class="compare-heatmap__scroller" bind:this={scroller}>
      <div class="compare-heatmap__grid" style={`--day-count: ${dates.length}`}>
        {#each rows as row}
          <div class="compare-heatmap__label" data-kind={row.kind}>{row.label}</div>
          {#each dates as date}
            {@const value = valueFor(row, date)}
            <button
              type="button"
              class={`compare-heatmap__cell compare-heatmap__cell--${heatmapLevel(value, maxValue)}`}
              data-kind={row.kind}
              aria-label={`${row.label}, ${date}: ${value}`}
              title={`${row.label}, ${date}: ${value}`}
              on:click={() => dispatch('selectDate', { date, rowId: row.id })}
            ></button>
          {/each}
        {/each}
      </div>
    </div>
    <div class="compare-heatmap__legend">
      <span>{$_('trends.heatmap.less')}</span>
      {#each [0, 1, 2, 3, 4] as level}
        <span class={`compare-heatmap__legend-cell compare-heatmap__cell--${level}`}></span>
      {/each}
      <span>{$_('trends.heatmap.more')}</span>
    </div>
  {:else}
    <div class="compare-heatmap__empty">{$_('trends.compare.empty_layers')}</div>
  {/if}
</section>

<style>
  .compare-heatmap {
    display: grid;
    gap: var(--space-3);
  }

  .compare-heatmap__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .compare-heatmap__head h3,
  .compare-heatmap__head span {
    margin: 0;
  }

  .compare-heatmap__head h3 {
    font-size: var(--text-base);
  }

  .compare-heatmap__head span,
  .compare-heatmap__legend,
  .compare-heatmap__empty {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .compare-heatmap__scroller {
    overflow-x: auto;
    padding-bottom: var(--space-1);
  }

  .compare-heatmap__grid {
    display: grid;
    grid-template-columns: minmax(7rem, 10rem) repeat(var(--day-count), 0.82rem);
    gap: 0.18rem;
    min-width: max-content;
    align-items: center;
  }

  .compare-heatmap__label {
    position: sticky;
    left: 0;
    z-index: 1;
    padding: var(--space-1) var(--space-2) var(--space-1) 0;
    background: var(--color-surface-chart-bg);
    color: var(--color-text);
    font-size: var(--text-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .compare-heatmap__label[data-kind='symptom'] {
    color: var(--color-primary);
  }

  .compare-heatmap__cell,
  .compare-heatmap__legend-cell {
    width: 0.82rem;
    height: 0.82rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-dynamic);
  }

  .compare-heatmap__cell:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .compare-heatmap__cell--1 {
    background: var(--color-heatmap-1);
  }

  .compare-heatmap__cell--2 {
    background: var(--color-heatmap-2);
  }

  .compare-heatmap__cell--3 {
    background: var(--color-heatmap-3);
  }

  .compare-heatmap__cell--4 {
    background: var(--color-heatmap-4);
  }

  .compare-heatmap__cell[data-kind='symptom'].compare-heatmap__cell--1 {
    background: color-mix(in srgb, var(--color-primary) 22%, var(--color-surface));
  }

  .compare-heatmap__cell[data-kind='symptom'].compare-heatmap__cell--2 {
    background: color-mix(in srgb, var(--color-primary) 38%, var(--color-surface));
  }

  .compare-heatmap__cell[data-kind='symptom'].compare-heatmap__cell--3 {
    background: color-mix(in srgb, var(--color-primary) 56%, var(--color-surface));
  }

  .compare-heatmap__cell[data-kind='symptom'].compare-heatmap__cell--4 {
    background: color-mix(in srgb, var(--color-primary) 72%, var(--color-surface));
  }

  .compare-heatmap__legend {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .compare-heatmap__empty {
    padding: var(--space-4);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-md);
  }

  @media (pointer: coarse) {
    .compare-heatmap__grid {
      grid-template-columns: minmax(7rem, 10rem) repeat(var(--day-count), 2.75rem);
      gap: 0.25rem;
    }

    .compare-heatmap__cell {
      width: 2.75rem;
      height: 2.75rem;
    }
  }
</style>
