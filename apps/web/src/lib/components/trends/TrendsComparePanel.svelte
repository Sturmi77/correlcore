<script lang="ts">
  import { browser } from '$app/environment';
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type {
    SymptomHeatmapResponse,
    TagHeatmapResponse,
    TimeseriesPoint,
    TimeseriesRange,
  } from '$lib/api/stats';
  import { buildIsoDateRange, compareDailyAxisLayout, type MetricKey } from '$lib/utils/charts';
  import {
    buildAxisBuckets,
    clampZoomStage,
    findBucketForDate,
    formatBucketRangeLabel,
    stageDays,
    type AxisBucket,
    type CompareZoomStageIndex,
  } from '$lib/utils/compareAxisZoom';
  import { compareDailyAxisLayoutFromRoot } from '$lib/utils/trendsDateAxis';
  import type { WorkContextHeatmapResponse } from '$lib/utils/workContextHeatmap';
  import {
    readCompareMode,
    readCompareSortMode,
    readCompareZoomStage,
    writeCompareMode,
    writeCompareSortMode,
    writeCompareZoomStage,
    type CompareMode,
    type CompareSortMode,
  } from '$lib/utils/comparePanelSettings';
  import { timelineCursor, timelineCursorDate } from '$lib/stores/timelineCursor';
  import MetricTimeseries from './MetricTimeseries.svelte';
  import ComparisonHeatmap from './ComparisonHeatmap.svelte';
  import UnifiedStripChart from './UnifiedStripChart.svelte';
  import type { EventMarker } from './EventMarkerLayer.svelte';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  export let enabled: Record<MetricKey, boolean>;
  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let workContextHeatmap: WorkContextHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let showWorkContexts = true;
  export let loading = false;
  export let pruneSparseAxes = false;
  export let compactChrome = false;
  export let mode: CompareMode = readCompareMode();
  export let sortMode: CompareSortMode = readCompareSortMode();
  /**
   * Sprint 1 (ADR-0035): event markers shared across metric chart and
   * heatmap rows. Computed by the parent page from insight maturity,
   * symptom onsets, and habit goal changes; passed unfiltered.
   */
  export let markers: readonly EventMarker[] = [];
  export let noteDates: readonly string[] = [];
  /**
   * Sprint 2 (ADR-0035): optional correlation map handed down to the
   * heatmap when sortMode === 'correlation'. Values are |r| in [0, 1].
   */
  export let correlationScores: Record<string, number> = {};

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    layerChange: { showTags: boolean; showSymptoms: boolean; showWorkContexts: boolean };
    modeChange: { value: CompareMode };
    sortChange: { value: CompareSortMode };
  }>();

  // Sprint 1 (ADR-0035): the Compare panel owns the cursor lifecycle.
  // #214 finding 4: scale day columns from root rem for accessible touch targets.
  let axisLayout = compareDailyAxisLayout;

  onMount(() => {
    const rootPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    axisLayout = compareDailyAxisLayoutFromRoot(rootPx);
    timelineCursor.reset();
  });
  onDestroy(() => {
    timelineCursor.reset();
  });

  const PINS_KEY = 'cc_trend_compare_pins';

  function readLocal<T>(key: string, fallback: T, isValid: (value: unknown) => boolean): T {
    if (!browser) return fallback;
    try {
      const raw = window.localStorage.getItem(key);
      if (raw === null) return fallback;
      const parsed = JSON.parse(raw);
      return isValid(parsed) ? (parsed as T) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeLocal(key: string, value: unknown): void {
    if (!browser) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Quota or private-mode — silently ignore. Preference falls back to default next session.
    }
  }

  let pinned: string[] = readLocal<string[]>(
    PINS_KEY,
    [],
    (value) => Array.isArray(value) && value.every((item) => typeof item === 'string')
  );

  let zoomStage: CompareZoomStageIndex = readCompareZoomStage();

  function setMode(next: CompareMode): void {
    mode = next;
    writeCompareMode(next);
    dispatch('modeChange', { value: next });
  }

  function setSortMode(next: CompareSortMode): void {
    sortMode = next;
    writeCompareSortMode(next);
    dispatch('sortChange', { value: next });
  }

  function setZoomStage(next: CompareZoomStageIndex): void {
    pendingFocusDate = null;
    zoomStage = next;
    writeCompareZoomStage(next);
    timelineCursor.clear();
  }

  function zoomOut(): void {
    setZoomStage(clampZoomStage(zoomStage + 1));
  }

  function zoomIn(): void {
    setZoomStage(clampZoomStage(zoomStage - 1));
  }

  /** CAZ-2: multi-day tap zooms one stage finer and keeps the interval in view. */
  function zoomInBucket(bucket: AxisBucket): void {
    if (mode !== 'lines' || zoomStage === 0 || bucket.dates.length <= 1) return;
    pendingFocusDate = bucket.start;
    zoomStage = clampZoomStage(zoomStage - 1);
    writeCompareZoomStage(zoomStage);
  }

  function handleZoomInBucket(event: CustomEvent<{ bucket: AxisBucket }>): void {
    zoomInBucket(event.detail.bucket);
  }

  function handlePinToggle(event: CustomEvent<{ rowId: string; pinned: boolean }>): void {
    const { rowId, pinned: shouldPin } = event.detail;
    pinned = shouldPin ? [...pinned, rowId] : pinned.filter((id) => id !== rowId);
    writeLocal(PINS_KEY, pinned);
  }

  let axisScroller: HTMLDivElement;
  let lastAxisKey = '';
  let pendingFocusDate: string | null = null;

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (axisScroller) axisScroller.scrollLeft = axisScroller.scrollWidth;
  }

  async function scrollDateIntoView(date: string): Promise<void> {
    await tick();
    if (!axisScroller) return;
    const targetBucket = findBucketForDate(axisBuckets, date);
    const focusKey = targetBucket?.start ?? date;
    const cell = axisScroller.querySelector(`[data-date="${focusKey}"]`);
    if (cell instanceof HTMLElement && typeof cell.scrollIntoView === 'function') {
      cell.scrollIntoView({ inline: 'center', block: 'nearest' });
    }
    timelineCursor.setDate(focusKey, 'tap');
  }

  $: axisStart =
    tagHeatmap?.start_date ??
    symptomHeatmap?.start_date ??
    workContextHeatmap?.start_date ??
    points[0]?.period_start ??
    '';
  $: axisEnd =
    tagHeatmap?.end_date ??
    symptomHeatmap?.end_date ??
    workContextHeatmap?.end_date ??
    points[points.length - 1]?.period_end ??
    points[points.length - 1]?.period_start ??
    '';
  $: axisDates = axisStart && axisEnd ? buildIsoDateRange(axisStart, axisEnd) : [];
  /**
   * Strip mode has no bucket aggregation yet (CAZ-3 follow-up) — force day
   * columns so Lines/Strips never disagree on the shared axis.
   */
  $: effectiveZoomStage = mode === 'strips' ? 0 : zoomStage;
  $: axisBuckets = buildAxisBuckets(axisDates, effectiveZoomStage);
  $: bucketAxisLayout =
    effectiveZoomStage === 0
      ? axisLayout
      : {
          ...axisLayout,
          dayWidth: Math.max(axisLayout.dayWidth, 28),
        };
  $: zoomDays = stageDays(effectiveZoomStage);
  $: canZoomOut = mode === 'lines' && zoomStage < 4;
  $: canZoomIn = mode === 'lines' && zoomStage > 0;
  $: axisKey = `${axisStart}:${axisEnd}:${axisDates.length}:${effectiveZoomStage}:${mode}`;
  $: if (axisKey && axisKey !== lastAxisKey) {
    lastAxisKey = axisKey;
    if (pendingFocusDate) {
      const focus = pendingFocusDate;
      pendingFocusDate = null;
      void scrollDateIntoView(focus);
    } else {
      void scrollToLatest();
    }
  }
  /** Kontextzeilen only make sense when the selected range has at least one entry. */
  $: hasEntriesInRange = points.some((point) => point.entry_count > 0);

  $: cursorBucket = $timelineCursorDate
    ? findBucketForDate(axisBuckets, $timelineCursorDate)
    : null;
  $: cursorEntryDays = cursorBucket
    ? cursorBucket.dates.reduce((count, date) => {
        const point = points.find((item) => item.period_start === date);
        return count + (point && point.entry_count > 0 ? 1 : 0);
      }, 0)
    : 0;
  $: cursorCoverageLabel = cursorBucket
    ? $_(
        cursorBucket.partial ? 'trends.compare.zoom.partial' : 'trends.compare.zoom.coverage',
        {
          values: cursorBucket.partial
            ? { present: cursorBucket.presentDays, size: cursorBucket.dayCount }
            : { active: cursorEntryDays, present: cursorBucket.presentDays },
        }
      )
    : '';
  $: cursorDetailLabel =
    cursorBucket && cursorCoverageLabel
      ? $_('trends.compare.zoom.detail', {
          values: {
            range: formatBucketRangeLabel(cursorBucket),
            coverage: cursorCoverageLabel,
          },
        })
      : '';
</script>

<section class="compare" class:compare--compact={compactChrome} data-testid="trends-compare-panel">
  {#if !compactChrome}
    <header class="compare__header">
      <div>
        <h2>{$_('trends.compare.heading')}</h2>
        <p>{$_('trends.compare.body')}</p>
      </div>
      <div class="compare__layers" aria-label={$_('trends.compare.layers')}>
        <label>
          <input
            type="checkbox"
            checked={showTags}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags: event.currentTarget.checked,
                showSymptoms,
                showWorkContexts,
              })}
          />
          {$_('trends.compare.tags')}
        </label>
        <label>
          <input
            type="checkbox"
            checked={showSymptoms}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags,
                showSymptoms: event.currentTarget.checked,
                showWorkContexts,
              })}
          />
          {$_('trends.compare.symptoms')}
        </label>
        <label>
          <input
            type="checkbox"
            checked={showWorkContexts}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags,
                showSymptoms,
                showWorkContexts: event.currentTarget.checked,
              })}
          />
          {$_('trends.compare.work_contexts')}
        </label>
      </div>
    </header>

    <div class="compare__controls" data-testid="trends-compare-controls">
      <div class="compare__mode" role="group" aria-label={$_('trends.compare.mode_label')}>
        <span class="compare__control-label">{$_('trends.compare.mode_label')}</span>
        <button
          type="button"
          class="compare__chip"
          class:compare__chip--active={mode === 'lines'}
          aria-pressed={mode === 'lines'}
          on:click={() => setMode('lines')}
        >
          {$_('trends.compare.mode_lines')}
        </button>
        <button
          type="button"
          class="compare__chip"
          class:compare__chip--active={mode === 'strips'}
          aria-pressed={mode === 'strips'}
          on:click={() => setMode('strips')}
        >
          {$_('trends.compare.mode_strips')}
        </button>
      </div>

      <label class="compare__sort">
        <span class="compare__control-label">{$_('trends.compare.sort_label')}</span>
        <select
          value={sortMode}
          on:change={(event) => setSortMode(event.currentTarget.value as CompareSortMode)}
        >
          <option value="frequency">{$_('trends.compare.sort_frequency')}</option>
          <option value="recent">{$_('trends.compare.sort_recent')}</option>
          <option value="correlation">{$_('trends.compare.sort_correlation')}</option>
          <option value="pinned">{$_('trends.compare.sort_pinned')}</option>
        </select>
      </label>
    </div>
  {/if}

  {#if axisDates.length > 0}
    <div class="compare__zoom-block" data-testid="trends-compare-zoom-block">
      <div
        class="compare__zoom"
        role="group"
        aria-label={$_('trends.compare.zoom.label')}
        data-testid="trends-compare-zoom"
      >
        <button
          type="button"
          class="compare__zoom-btn"
          data-testid="trends-compare-zoom-decrease"
          aria-label={$_('trends.compare.zoom.decrease_aria')}
          disabled={!canZoomOut}
          on:click={zoomOut}
        >
          −
        </button>
        <span class="compare__zoom-status" data-testid="trends-compare-zoom-status">
          {$_('trends.compare.zoom.status', { values: { days: zoomDays } })}
        </span>
        <button
          type="button"
          class="compare__zoom-btn"
          data-testid="trends-compare-zoom-increase"
          aria-label={$_('trends.compare.zoom.increase_aria')}
          disabled={!canZoomIn}
          on:click={zoomIn}
        >
          +
        </button>
      </div>
      <p class="compare__zoom-hint" data-testid="trends-compare-zoom-encoding">
        {$_('trends.compare.zoom.encoding_hint')}
      </p>
      {#if mode === 'lines' && zoomStage > 0}
        <p class="compare__zoom-hint" data-testid="trends-compare-zoom-tap-hint">
          {$_('trends.compare.zoom.tap_hint')}
        </p>
      {/if}
      {#if cursorDetailLabel}
        <p class="compare__zoom-detail" data-testid="trends-compare-zoom-detail">
          {cursorDetailLabel}
        </p>
      {/if}
    </div>
  {/if}

  <div
    class="compare__axis-scroller"
    bind:this={axisScroller}
    aria-label={$_('trends.compare.shared_axis')}
  >
    {#if mode === 'strips'}
      <UnifiedStripChart
        {points}
        {enabled}
        {loading}
        {axisDates}
        axisLayout={bucketAxisLayout}
        {markers}
        enableCursor
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
      />
    {:else}
      <MetricTimeseries
        {points}
        {range}
        {enabled}
        {loading}
        {axisDates}
        buckets={axisBuckets}
        axisLayout={bucketAxisLayout}
        {markers}
        {noteDates}
        enableCursor
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
        on:zoomInBucket={handleZoomInBucket}
      />
    {/if}

    {#if hasEntriesInRange}
      <ComparisonHeatmap
        {tagHeatmap}
        {symptomHeatmap}
        {workContextHeatmap}
        {showTags}
        {showSymptoms}
        {showWorkContexts}
        {loading}
        dates={axisDates}
        buckets={axisBuckets}
        axisLayout={bucketAxisLayout}
        {markers}
        enableCursor
        {sortMode}
        {pinned}
        {correlationScores}
        scrollable={false}
        autoScroll={false}
        {pruneSparseAxes}
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
        on:zoomInBucket={handleZoomInBucket}
        on:pinToggle={handlePinToggle}
      />
    {/if}
  </div>
</section>

<style>
  .compare {
    display: grid;
    gap: var(--space-4);
  }

  .compare--compact {
    gap: 0;
  }

  .compare__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .compare__header h2,
  .compare__header p {
    margin: 0;
  }

  .compare__header h2 {
    font-size: var(--text-lg);
  }

  .compare__header p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .compare__layers {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--space-2);
  }

  .compare__layers label {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .compare__axis-scroller {
    display: grid;
    gap: var(--space-4);
    overflow-x: auto;
    padding-bottom: var(--space-2);
  }

  /* Sprint 2 (ADR-0035) — token-only, hue-agnostic controls. */
  .compare__controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
  }

  .compare__mode {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    background: var(--color-strip-track-bg);
    border-radius: var(--radius-md, 8px);
    padding: 2px;
  }

  .compare__control-label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    padding: 0 var(--space-1);
  }

  .compare__chip {
    background: transparent;
    border: 0;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    color: var(--color-text);
    cursor: pointer;
    font-size: var(--text-sm);
    font-weight: 600;
    min-height: var(--tap-target);
  }

  .compare__chip--active {
    background: var(--color-surface);
    color: var(--color-fg);
    box-shadow: 0 0 0 1px var(--color-border-chart, var(--color-cursor-halo));
  }

  .compare__chip:focus-visible {
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 1px;
  }

  .compare__sort {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-sm);
  }

  .compare__sort select {
    min-height: var(--tap-target);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }

  .compare__zoom-block {
    display: grid;
    gap: var(--space-1);
  }

  .compare__zoom {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .compare__zoom-hint,
  .compare__zoom-detail {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .compare__zoom-detail {
    font-weight: 600;
  }

  .compare__zoom-btn {
    min-width: var(--tap-target);
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--text-lg);
    font-weight: 700;
    line-height: 1;
    cursor: pointer;
  }

  .compare__zoom-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .compare__zoom-btn:focus-visible {
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 1px;
  }

  .compare__zoom-status {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 600;
    min-width: 7rem;
    text-align: center;
  }

  @media (max-width: 480px) {
    .compare__header {
      flex-direction: column;
    }

    .compare__layers {
      justify-content: flex-start;
    }
  }
</style>
