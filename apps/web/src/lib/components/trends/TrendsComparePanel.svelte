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
  import { compareDailyAxisLayoutFromRoot } from '$lib/utils/trendsDateAxis';
  import type { WorkContextHeatmapResponse } from '$lib/utils/workContextHeatmap';
  import {
    readCompareMode,
    readCompareSortMode,
    writeCompareMode,
    writeCompareSortMode,
    type CompareMode,
    type CompareSortMode,
  } from '$lib/utils/comparePanelSettings';
  import { timelineCursor } from '$lib/stores/timelineCursor';
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

  function handlePinToggle(event: CustomEvent<{ rowId: string; pinned: boolean }>): void {
    const { rowId, pinned: shouldPin } = event.detail;
    pinned = shouldPin ? [...pinned, rowId] : pinned.filter((id) => id !== rowId);
    writeLocal(PINS_KEY, pinned);
  }

  let axisScroller: HTMLDivElement;
  let lastAxisKey = '';

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (axisScroller) axisScroller.scrollLeft = axisScroller.scrollWidth;
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
  $: axisKey = `${axisStart}:${axisEnd}:${axisDates.length}`;
  $: if (axisKey && axisKey !== lastAxisKey) {
    lastAxisKey = axisKey;
    void scrollToLatest();
  }
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
        {axisLayout}
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
        {axisLayout}
        {markers}
        enableCursor
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
      />
    {/if}

    <ComparisonHeatmap
      {tagHeatmap}
      {symptomHeatmap}
      {workContextHeatmap}
      {showTags}
      {showSymptoms}
      {showWorkContexts}
      {loading}
      dates={axisDates}
      {axisLayout}
      {markers}
      enableCursor
      {sortMode}
      {pinned}
      {correlationScores}
      scrollable={false}
      autoScroll={false}
      {pruneSparseAxes}
      on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
      on:pinToggle={handlePinToggle}
    />
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
    min-height: 32px;
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
    min-height: 36px;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }

  @media (max-width: 640px) {
    .compare__header {
      flex-direction: column;
    }

    .compare__layers {
      justify-content: flex-start;
    }
  }
</style>
