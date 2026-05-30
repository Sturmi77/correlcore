<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
  import {
    buildIsoDateRange,
    compareDailyAxisLayout,
    heatmapLevel,
    type DailyAxisLayout,
  } from '$lib/utils/charts';
  import { timelineCursor } from '$lib/stores/timelineCursor';
  import type { EventMarker } from './EventMarkerLayer.svelte';

  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let loading = false;
  export let dates: string[] = [];
  export let axisLayout: DailyAxisLayout = compareDailyAxisLayout;
  export let scrollable = true;
  export let autoScroll = true;
  export let headingKey = 'trends.compare.heatmap_heading';
  export let emptyKey = 'trends.compare.empty_layers';
  /**
   * Sprint 1 (ADR-0035): enables hover synchronisation with the shared
   * timeline cursor. When true, cell hover publishes to the cursor
   * store and the matching column is highlighted via cursor state.
   */
  export let enableCursor = false;
  /**
   * Sprint 1 (ADR-0035): event markers rendered as full-height vertical
   * lines/bands across the heatmap grid.
   */
  export let markers: readonly EventMarker[] = [];

  const dispatch = createEventDispatcher<{ selectDate: { date: string; rowId: string } }>();

  type Row = {
    id: string;
    label: string;
    kind: 'tag' | 'symptom';
    days: { date: string; count: number; max_intensity?: number }[];
  };

  let scroller: HTMLDivElement;
  let lastKey = '';

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
  $: axisDates =
    dates.length > 0 ? dates : startDate && endDate ? buildIsoDateRange(startDate, endDate) : [];
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
  $: maxValue = Math.max(0, ...rows.flatMap((row) => axisDates.map((date) => valueFor(row, date))));
  $: scrollKey = `${startDate}:${endDate}:${rows.length}`;
  $: gridStyle = [
    `--day-count: ${axisDates.length}`,
    `--axis-label-width: ${axisLayout.labelWidth}px`,
    `--axis-day-width: ${axisLayout.dayWidth}px`,
    `--axis-gap: ${axisLayout.dayGap}px`,
  ].join('; ');
  $: if (autoScroll && scrollKey && scrollKey !== lastKey) {
    lastKey = scrollKey;
    void scrollToLatest();
  }

  // Sprint 1 (ADR-0035): mirror the cursor store to a local class for CSS
  // column highlighting via [data-date] selectors.
  $: cursorDate = $timelineCursor.date;
  $: markerDateSet = new Set(markers.map((m) => m.date));
  $: markerBandDates = markers
    .filter((m) => m.endDate)
    .flatMap((m) => buildIsoDateRange(m.date, m.endDate ?? m.date));
  $: markerBandSet = new Set(markerBandDates);

  function handleCellEnter(date: string) {
    if (!enableCursor) return;
    timelineCursor.hover(date);
  }

  function handleCellLeave() {
    if (!enableCursor) return;
    timelineCursor.hover(null);
  }
</script>

<section class="compare-heatmap" data-loading={loading ? 'true' : 'false'}>
  <header class="compare-heatmap__head">
    <h3>{$_(headingKey)}</h3>
    {#if axisDates.length > 0}
      <span>{axisDates[0]} - {axisDates[axisDates.length - 1]}</span>
    {/if}
  </header>

  {#if loading && rows.length === 0}
    <div class="compare-heatmap__empty" role="status">{$_('trends.compare.loading')}</div>
  {:else if rows.length > 0}
    <div
      class="compare-heatmap__scroller"
      data-scrollable={scrollable ? 'true' : 'false'}
      bind:this={scroller}
    >
      <div class="compare-heatmap__grid" style={gridStyle}>
        {#each rows as row}
          <div class="compare-heatmap__label" data-kind={row.kind}>{row.label}</div>
          {#each axisDates as date}
            {@const value = valueFor(row, date)}
            <button
              type="button"
              class={`compare-heatmap__cell compare-heatmap__cell--${heatmapLevel(value, maxValue)}`}
              class:compare-heatmap__cell--cursor={enableCursor && cursorDate === date}
              class:compare-heatmap__cell--marker={markerDateSet.has(date)}
              class:compare-heatmap__cell--marker-band={markerBandSet.has(date)}
              data-kind={row.kind}
              data-date={date}
              aria-label={`${row.label}, ${date}: ${value}`}
              title={`${row.label}, ${date}: ${value}`}
              on:click={() => dispatch('selectDate', { date, rowId: row.id })}
              on:pointerenter={() => handleCellEnter(date)}
              on:pointerleave={handleCellLeave}
              on:focus={() => enableCursor && timelineCursor.focus(date)}
              on:blur={() => enableCursor && timelineCursor.hover(null)}
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
    <div class="compare-heatmap__empty">{$_(emptyKey)}</div>
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

  .compare-heatmap__scroller[data-scrollable='false'] {
    overflow-x: visible;
    padding-bottom: 0;
  }

  .compare-heatmap__grid {
    display: grid;
    grid-template-columns: var(--axis-label-width) repeat(var(--day-count), var(--axis-day-width));
    column-gap: var(--axis-gap);
    row-gap: 0.18rem;
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
    width: var(--axis-day-width);
    height: var(--axis-day-width);
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

  /* Sprint 1 (ADR-0035): cursor + marker highlights — theme-agnostic */
  .compare-heatmap__cell--cursor {
    box-shadow:
      0 0 0 2px var(--color-cursor),
      0 0 0 5px var(--color-cursor-halo);
    position: relative;
    z-index: 1;
  }

  .compare-heatmap__cell--marker-band {
    outline: 1px solid var(--color-event-marker-soft);
    outline-offset: -1px;
  }

  .compare-heatmap__cell--marker {
    border-left: 2px dashed var(--color-event-marker);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
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
</style>
