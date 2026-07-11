<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import TabBar, { type TabBarOption } from '$lib/components/common/TabBar.svelte';
  import type { TimeseriesRange } from '$lib/api/stats';

  export let analysisRange: TimeseriesRange;
  export let analysisRangeOptions: SegmentedControlOption[] = [];
  export let activeTab: string;
  export let tabOptions: TabBarOption[] = [];
  export let showCompareFilters = false;

  const dispatch = createEventDispatcher<{
    rangeChange: { value: TimeseriesRange };
    tabChange: { value: string };
  }>();
</script>

<div class="trends-toolbar" data-testid="trends-analysis-toolbar">
  <div class="trends-toolbar__row trends-toolbar__row--range" data-testid="trends-sticky-toolbar">
    <SegmentedControl
      value={analysisRange}
      options={analysisRangeOptions}
      ariaLabel={$_('trends.controls')}
      testId="trends-range-control"
      on:change={(event) =>
        dispatch('rangeChange', { value: event.detail.value as TimeseriesRange })}
    />
  </div>

  <div class="trends-toolbar__row" data-testid="trends-tabs-toolbar">
    <TabBar
      value={activeTab}
      options={tabOptions}
      ariaLabel={$_('trends.tabs.label')}
      testId="trends-tabs"
      on:change={(event) => dispatch('tabChange', { value: event.detail.value })}
    />
  </div>

  {#if showCompareFilters}
    <div
      class="trends-toolbar__row trends-toolbar__row--filters"
      data-testid="trends-filters-toolbar"
    >
      <slot name="compare-filters" />
    </div>
  {/if}
</div>

<style>
  .trends-toolbar {
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

  .trends-toolbar__row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-2);
    min-width: 0;
  }

  .trends-toolbar__row--filters {
    padding-top: var(--space-1);
    border-top: 1px solid var(--color-border);
  }

  @media (max-width: 520px) {
    .trends-toolbar {
      padding: var(--space-2);
      gap: var(--space-1);
    }

    .trends-toolbar__row {
      gap: var(--space-2);
    }
  }
</style>
