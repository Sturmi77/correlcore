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
  import {
    countBucketActiveDays,
    formatBucketRangeLabel,
    sumBucketCounts,
    type AxisBucket,
  } from '$lib/utils/compareAxisZoom';
  import { pruneHeatmapRows, pruneHeatmapRowsByBuckets } from '$lib/utils/heatmapPruning';
  import { timelineCursor } from '$lib/stores/timelineCursor';
  import type { TagClusterMeta } from '$lib/utils/tagCooccurrenceMatrix';
  import type { WorkContextHeatmapResponse } from '$lib/utils/workContextHeatmap';
  import type { EventMarker } from './EventMarkerLayer.svelte';

  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let workContextHeatmap: WorkContextHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let showWorkContexts = true;
  export let loading = false;
  export let dates: string[] = [];
  /** When set, render one column per bucket (shared Compare zoom axis). */
  export let buckets: readonly AxisBucket[] = [];
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
  /**
   * Sprint 2 (ADR-0035): row sorting mode. Pure presentation — the parent
   * component owns the persisted preference. 'correlation' falls back to
   * 'frequency' when no correlationScores map is supplied.
   */
  export let sortMode: 'frequency' | 'recent' | 'correlation' | 'pinned' | 'clustered' =
    'frequency';
  /**
   * Sprint 2 (ADR-0035): row ids that should float to the top regardless
   * of the sort mode. Persisted by the parent.
   */
  export let pinned: readonly string[] = [];
  /**
   * Sprint 2 (ADR-0035): optional correlation strength per row id, used
   * when sortMode === 'correlation'. Values are |r| in [0, 1].
   */
  export let correlationScores: Record<string, number> = {};
  /**
   * When true, hide rows with zero values in the selected range.
   * Date columns are never pruned here: Compare stacks this heatmap under
   * MetricTimeseries / UnifiedStripChart on a shared `dates` axis, and
   * dropping empty days would shift cells out of alignment with the chart.
   */
  export let pruneSparseAxes = true;
  /** Server tag groups (#592); empty maps when insufficient_data. */
  export let clusterMeta: TagClusterMeta = { byTagId: new Map(), labels: [] };
  /** Focused cluster id, or null for all tag rows. */
  export let focusedClusterId: number | null = null;
  $: if (
    !loading &&
    focusedClusterId !== null &&
    clustersAvailable &&
    !rawRows.some(
      (row) => row.kind === 'tag' && clusterMeta.byTagId.get(row.id) === focusedClusterId
    )
  ) {
    focusedClusterId = null;
  }

  const UNGROUPED_CLUSTER = Number.POSITIVE_INFINITY;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string; rowId: string };
    zoomInBucket: { bucket: AxisBucket };
    pinToggle: { rowId: string; pinned: boolean };
  }>();

  type Row = {
    id: string;
    label: string;
    kind: 'tag' | 'symptom' | 'work_context';
    days: { date: string; count: number; max_intensity?: number }[];
  };

  let scroller: HTMLDivElement;
  let lastKey = '';

  function valueFor(row: Row, date: string): number {
    const day = row.days.find((item) => item.date === date);
    if (!day) return 0;
    if (row.kind === 'symptom') return day.max_intensity ?? day.count;
    return day.count;
  }

  function countFor(row: Row, date: string): number {
    return row.days.find((item) => item.date === date)?.count ?? 0;
  }

  function valueForBucket(row: Row, bucket: AxisBucket): number {
    if (bucket.dates.length === 1) {
      return valueFor(row, bucket.dates[0]!);
    }
    return sumBucketCounts((date) => countFor(row, date), bucket);
  }

  function cellTooltip(row: Row, bucket: AxisBucket, value: number): string {
    const range = formatBucketRangeLabel(bucket);
    const active = countBucketActiveDays((date) => countFor(row, date), bucket);
    const coverage = bucket.partial
      ? $_('trends.compare.zoom.partial', {
          values: { present: bucket.presentDays, size: bucket.dayCount },
        })
      : $_('trends.compare.zoom.coverage', {
          values: { active, present: bucket.presentDays },
        });
    const key =
      bucket.dates.length > 1
        ? 'trends.compare.zoom.cell_tooltip_zoom'
        : 'trends.compare.zoom.cell_tooltip';
    return $_(key, {
      values: { label: row.label, range, value, coverage },
    });
  }

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (scroller) scroller.scrollLeft = scroller.scrollWidth;
  }

  $: startDate =
    tagHeatmap?.start_date ?? symptomHeatmap?.start_date ?? workContextHeatmap?.start_date ?? '';
  $: endDate =
    tagHeatmap?.end_date ?? symptomHeatmap?.end_date ?? workContextHeatmap?.end_date ?? '';
  $: axisDates =
    dates.length > 0 ? dates : startDate && endDate ? buildIsoDateRange(startDate, endDate) : [];
  $: rawRows = [
    ...(showTags
      ? (tagHeatmap?.tags ?? []).map((tag): Row => ({
          id: tag.tag_id,
          label: tag.name,
          kind: 'tag',
          days: tag.days,
        }))
      : []),
    ...(showSymptoms
      ? (symptomHeatmap?.symptoms ?? []).map((symptom): Row => ({
          id: symptom.symptom_id,
          label: symptom.name,
          kind: 'symptom',
          days: symptom.days,
        }))
      : []),
    ...(showWorkContexts
      ? (workContextHeatmap?.contexts ?? []).map((context): Row => ({
          id: `work_context:${context.context}`,
          label: $_(`entry.work_context.${context.context}`),
          kind: 'work_context',
          days: context.days,
        }))
      : []),
  ];

  function rowScore(row: Row): number {
    if (sortMode === 'recent') {
      let maxIdx = -1;
      for (let i = 0; i < row.days.length; i += 1) {
        const d = row.days[i];
        if ((d.count ?? 0) > 0 && d.date > (row.days[maxIdx]?.date ?? '')) {
          maxIdx = i;
        }
      }
      return maxIdx === -1 ? 0 : Date.parse(row.days[maxIdx].date);
    }
    if (sortMode === 'correlation') {
      const score = correlationScores[row.id];
      if (typeof score === 'number') return score;
      // Fallback to frequency when no correlation is available.
    }
    // 'frequency' and fallback path.
    return row.days.reduce((sum, d) => sum + (d.count ?? 0), 0);
  }

  function clusterOrder(left: Row, right: Row): number {
    const leftCluster = clusterMeta.byTagId.get(left.id) ?? UNGROUPED_CLUSTER;
    const rightCluster = clusterMeta.byTagId.get(right.id) ?? UNGROUPED_CLUSTER;
    if (leftCluster !== rightCluster) return leftCluster - rightCluster;
    return left.label.localeCompare(right.label, undefined, { sensitivity: 'base' });
  }

  function kindRank(kind: Row['kind']): number {
    if (kind === 'tag') return 0;
    if (kind === 'symptom') return 1;
    return 2;
  }

  function defaultRowSort(a: Row, b: Row): number {
    if (sortMode === 'pinned') {
      return (
        b.days.reduce((s, d) => s + (d.count ?? 0), 0) -
          a.days.reduce((s, d) => s + (d.count ?? 0), 0) || a.label.localeCompare(b.label)
      );
    }
    const delta = rowScore(b) - rowScore(a);
    if (delta !== 0) return delta;
    return a.label.localeCompare(b.label);
  }

  $: clustersAvailable = clusterMeta.labels.length > 0;
  $: clusterSortActive =
    sortMode === 'clustered' &&
    clustersAvailable &&
    rawRows.some((row) => row.kind === 'tag' && clusterMeta.byTagId.has(row.id));
  $: clusterFilteredRows =
    focusedClusterId !== null && clustersAvailable
      ? (() => {
          const focusedTags = rawRows.filter(
            (row) => row.kind === 'tag' && clusterMeta.byTagId.get(row.id) === focusedClusterId
          );
          if (focusedTags.length === 0) return rawRows;
          return rawRows.filter(
            (row) => row.kind !== 'tag' || clusterMeta.byTagId.get(row.id) === focusedClusterId
          );
        })()
      : rawRows;

  $: pinnedOrder = new Map(pinned.map((id, idx) => [id, idx]));
  $: sortedRows = [...clusterFilteredRows].sort((a, b) => {
    const aPin = pinnedOrder.get(a.id);
    const bPin = pinnedOrder.get(b.id);
    if (aPin !== undefined && bPin !== undefined) return aPin - bPin;
    if (aPin !== undefined) return -1;
    if (bPin !== undefined) return 1;
    if (clusterSortActive) {
      const kindDelta = kindRank(a.kind) - kindRank(b.kind);
      if (kindDelta !== 0) return kindDelta;
      if (a.kind === 'tag' && b.kind === 'tag') {
        return clusterOrder(a, b);
      }
    }
    return defaultRowSort(a, b);
  });
  // Prefer explicit zoom buckets from the Compare panel; otherwise one column per day.
  $: visibleBuckets =
    buckets.length > 0
      ? buckets
      : axisDates.map((date): AxisBucket => ({
          id: `${date}_${date}`,
          start: date,
          end: date,
          dayCount: 1,
          presentDays: 1,
          partial: false,
          dates: [date],
        }));
  $: rows = pruneSparseAxes
    ? visibleBuckets.length > 0
      ? pruneHeatmapRowsByBuckets(sortedRows, visibleBuckets, (row, bucket) =>
          valueForBucket(row, bucket)
        )
      : pruneHeatmapRows(sortedRows, axisDates, (row, date) => valueFor(row, date))
    : sortedRows;
  $: showClusterGaps = clusterSortActive && focusedClusterId === null;
  $: clusterBoundaries = showClusterGaps
    ? rows.map((row, index) => {
        if (row.kind !== 'tag') return false;
        for (let previous = index - 1; previous >= 0; previous -= 1) {
          const prior = rows[previous];
          if (prior.kind !== 'tag') continue;
          return clusterMeta.byTagId.get(row.id) !== clusterMeta.byTagId.get(prior.id);
        }
        return false;
      })
    : rows.map(() => false);
  $: visibleAxisDates = visibleBuckets.map((bucket) => bucket.start);
  $: maxValue = Math.max(
    0,
    ...rows.flatMap((row) => visibleBuckets.map((bucket) => valueForBucket(row, bucket)))
  );
  $: scrollKey = `${startDate}:${endDate}:${rows.length}:${visibleBuckets.length}`;
  $: gridStyle = [
    `--day-count: ${visibleBuckets.length}`,
    `--axis-label-width: ${axisLayout.labelWidth}px`,
    `--axis-day-width: ${axisLayout.dayWidth}px`,
    `--axis-gap: ${axisLayout.dayGap}px`,
  ].join('; ');
  $: if (autoScroll && scrollKey && scrollKey !== lastKey) {
    lastKey = scrollKey;
    void scrollToLatest();
  }

  // Sprint 1 (ADR-0035): mirror the cursor store to a local class for CSS
  // column highlighting via [data-date] selectors (bucket start = display key).
  $: cursorDate = $timelineCursor.date;
  $: markerDateSet = new Set(markers.map((m) => m.date));
  $: markerBandDates = markers
    .filter((m) => m.endDate)
    .flatMap((m) => buildIsoDateRange(m.date, m.endDate ?? m.date));
  $: markerBandSet = new Set(markerBandDates);

  function bucketHasMarker(bucket: AxisBucket): boolean {
    return bucket.dates.some((date) => markerDateSet.has(date));
  }

  function bucketHasMarkerBand(bucket: AxisBucket): boolean {
    return bucket.dates.some((date) => markerBandSet.has(date));
  }

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
    {#if visibleAxisDates.length > 0}
      <span>{visibleAxisDates[0]} - {visibleAxisDates[visibleAxisDates.length - 1]}</span>
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
        {#each rows as row, rowIndex (row.id)}
          <div
            class="compare-heatmap__label"
            class:compare-heatmap__boundary-top={clusterBoundaries[rowIndex]}
            data-kind={row.kind}
          >
            <button
              type="button"
              class="compare-heatmap__pin"
              class:compare-heatmap__pin--active={pinnedOrder.has(row.id)}
              aria-pressed={pinnedOrder.has(row.id)}
              aria-label={pinnedOrder.has(row.id)
                ? $_('trends.compare.unpin_aria')
                : $_('trends.compare.pin_aria')}
              on:click={() =>
                dispatch('pinToggle', { rowId: row.id, pinned: !pinnedOrder.has(row.id) })}
            >
              {pinnedOrder.has(row.id) ? '★' : '☆'}
            </button>
            <span class="compare-heatmap__label-text">{row.label}</span>
          </div>
          {#each visibleBuckets as bucket (bucket.id)}
            {@const value = valueForBucket(row, bucket)}
            {@const columnKey = bucket.start}
            {@const tooltip = cellTooltip(row, bucket, value)}
            <button
              type="button"
              class={`compare-heatmap__cell compare-heatmap__cell--${heatmapLevel(value, maxValue)}`}
              class:compare-heatmap__boundary-top={clusterBoundaries[rowIndex]}
              class:compare-heatmap__cell--cursor={enableCursor && cursorDate === columnKey}
              class:compare-heatmap__cell--marker={bucketHasMarker(bucket)}
              class:compare-heatmap__cell--marker-band={bucketHasMarkerBand(bucket)}
              class:compare-heatmap__cell--partial={bucket.partial}
              data-kind={row.kind}
              data-date={columnKey}
              data-bucket-end={bucket.end}
              data-partial={bucket.partial ? 'true' : 'false'}
              data-zoomable={bucket.dates.length > 1 ? 'true' : 'false'}
              aria-label={tooltip}
              title={tooltip}
              on:click={() => {
                if (bucket.dates.length === 1) {
                  dispatch('selectDate', { date: columnKey, rowId: row.id });
                } else {
                  dispatch('zoomInBucket', { bucket });
                }
              }}
              on:pointerenter={() => handleCellEnter(columnKey)}
              on:pointerleave={handleCellLeave}
              on:focus={() => enableCursor && timelineCursor.focus(columnKey)}
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
    row-gap: var(--heatmap-cell-gap);
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
    display: flex;
    align-items: center;
    gap: var(--space-1);
    min-width: 0;
  }

  .compare-heatmap__label-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1 1 auto;
    min-width: 0;
  }

  .compare-heatmap__label[data-kind='symptom'] .compare-heatmap__label-text {
    color: var(--color-primary);
  }

  .compare-heatmap__label[data-kind='work_context'] .compare-heatmap__label-text {
    color: var(--color-text-muted);
    font-weight: 700;
  }

  /* Tag-group cluster gap (#592): opens space where a new cluster begins. */
  .compare-heatmap__boundary-top {
    margin-top: var(--space-2);
    box-shadow: inset 0 1px 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent);
  }

  .compare-heatmap__pin {
    /* Theme-token only — no hue hardcoded. ADR-0035 §10. */
    background: transparent;
    border: 0;
    padding: 2px 4px;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: var(--text-sm);
    line-height: 1;
    border-radius: var(--radius-sm);
  }

  .compare-heatmap__pin:hover,
  .compare-heatmap__pin:focus-visible {
    color: var(--color-fg);
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 1px;
  }

  .compare-heatmap__pin--active {
    color: var(--color-event-marker);
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

  .compare-heatmap__cell--partial {
    opacity: 0.72;
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

  .compare-heatmap__cell[data-kind='work_context'].compare-heatmap__cell--1,
  .compare-heatmap__cell[data-kind='work_context'].compare-heatmap__cell--2,
  .compare-heatmap__cell[data-kind='work_context'].compare-heatmap__cell--3,
  .compare-heatmap__cell[data-kind='work_context'].compare-heatmap__cell--4 {
    background: color-mix(in srgb, var(--color-text-muted) 34%, var(--color-surface));
  }

  .compare-heatmap__legend {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .compare-heatmap__legend-cell {
    min-width: 0.9rem;
    min-height: 0.9rem;
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-text-muted) 32%, transparent);
  }

  .compare-heatmap__empty {
    padding: var(--space-4);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-md);
  }
</style>
