<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type {
    SymptomHeatmapResponse,
    TagHeatmapResponse,
    TimeseriesPoint,
    TimeseriesRange,
  } from '$lib/api/stats';
  import { buildIsoDateRange, compareDailyAxisLayout, type MetricKey } from '$lib/utils/charts';
  import MetricTimeseries from './MetricTimeseries.svelte';
  import ComparisonHeatmap from './ComparisonHeatmap.svelte';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  export let enabled: Record<MetricKey, boolean>;
  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let loading = false;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    layerChange: { showTags: boolean; showSymptoms: boolean };
  }>();

  let axisScroller: HTMLDivElement;
  let lastAxisKey = '';

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (axisScroller) axisScroller.scrollLeft = axisScroller.scrollWidth;
  }

  $: axisStart =
    tagHeatmap?.start_date ?? symptomHeatmap?.start_date ?? points[0]?.period_start ?? '';
  $: axisEnd =
    tagHeatmap?.end_date ??
    symptomHeatmap?.end_date ??
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

<section class="compare" data-testid="trends-compare-panel">
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
            })}
        />
        {$_('trends.compare.symptoms')}
      </label>
    </div>
  </header>

  <div
    class="compare__axis-scroller"
    bind:this={axisScroller}
    aria-label={$_('trends.compare.shared_axis')}
  >
    <MetricTimeseries
      {points}
      {range}
      {enabled}
      {loading}
      {axisDates}
      axisLayout={compareDailyAxisLayout}
      on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
    />

    <ComparisonHeatmap
      {tagHeatmap}
      {symptomHeatmap}
      {showTags}
      {showSymptoms}
      {loading}
      dates={axisDates}
      axisLayout={compareDailyAxisLayout}
      scrollable={false}
      autoScroll={false}
      on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
    />
  </div>
</section>

<style>
  .compare {
    display: grid;
    gap: var(--space-4);
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

  @media (max-width: 640px) {
    .compare__header {
      flex-direction: column;
    }

    .compare__layers {
      justify-content: flex-start;
    }
  }
</style>
