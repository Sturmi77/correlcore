<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import TabBar from '$lib/components/common/TabBar.svelte';
  import type { TimeseriesRange } from '$lib/api/stats';
  import type { InsightFeedFilterTab } from '$lib/utils/insightFeedFilter';

  export let analysisRange: TimeseriesRange;
  export let analysisRangeOptions: SegmentedControlOption[] = [];
  export let filterTab: InsightFeedFilterTab = 'all';
  export let filterTabOptions: { id: string; label: string }[] = [];
  export let showMatrixTab = false;
  export let detailView: 'findings' | 'matrix' = 'findings';

  const dispatch = createEventDispatcher<{
    rangeChange: { value: TimeseriesRange };
    filterChange: { value: InsightFeedFilterTab };
    matrixClick: void;
    findingsClick: void;
  }>();
</script>

<div class="insights-toolbar" data-testid="insights-analysis-toolbar">
  <div
    class="insights-toolbar__row insights-toolbar__row--range"
    data-testid="insights-sticky-toolbar"
  >
    <SegmentedControl
      value={analysisRange}
      options={analysisRangeOptions}
      ariaLabel={$_('insights.page.analysis_range_label')}
      testId="insights-range-control"
      on:change={(event) =>
        dispatch('rangeChange', { value: event.detail.value as TimeseriesRange })}
    />
  </div>

  {#if detailView === 'matrix'}
    <div class="insights-toolbar__row" data-testid="insights-findings-toolbar">
      <button
        type="button"
        class="insights-toolbar__view-link"
        data-testid="insights-findings-link"
        on:click={() => dispatch('findingsClick')}
      >
        {$_('insights.page.findings_view')}
      </button>
    </div>
  {:else}
    <div class="insights-toolbar__row" data-testid="insights-findings-toolbar">
      <TabBar
        value={filterTab}
        options={filterTabOptions}
        ariaLabel={$_('insights.feed.filter_label')}
        testId="insights-filter-tabs"
        on:change={(event) =>
          dispatch('filterChange', { value: event.detail.value as InsightFeedFilterTab })}
      />
      {#if showMatrixTab}
        <button
          type="button"
          class="insights-toolbar__view-link"
          data-testid="insights-matrix-link"
          on:click={() => dispatch('matrixClick')}
        >
          {$_('insights.page.matrix_view')}
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .insights-toolbar {
    position: sticky;
    top: calc(var(--app-header-height, 0px) + var(--space-2));
    z-index: 3;
    display: grid;
    gap: var(--space-2);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
    backdrop-filter: blur(8px);
  }

  .insights-toolbar__row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-width: 0;
  }

  .insights-toolbar__row--range {
    padding-bottom: var(--space-1);
    border-bottom: 1px solid var(--color-border);
  }

  .insights-toolbar__view-link {
    flex-shrink: 0;
    margin-left: auto;
    border: none;
    background: none;
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 600;
    cursor: pointer;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-sm);
  }

  .insights-toolbar__view-link:hover,
  .insights-toolbar__view-link:focus-visible {
    background: var(--color-primary-highlight);
    outline: none;
  }

  @media (max-width: 520px) {
    .insights-toolbar {
      padding: var(--space-2);
      gap: var(--space-1);
    }

    .insights-toolbar__row {
      flex-wrap: wrap;
      gap: var(--space-2);
    }
  }
</style>
