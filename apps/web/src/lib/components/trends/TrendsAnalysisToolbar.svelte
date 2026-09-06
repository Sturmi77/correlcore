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
  export let embedCompareFilters = true;
  /** Compare uses a fixed 365d zoom axis — hide range chips there (CAZ-0). */
  export let showRangeControl = true;

  const dispatch = createEventDispatcher<{
    rangeChange: { value: TimeseriesRange };
    tabChange: { value: string };
  }>();
</script>

<div class="trends-toolbar" data-testid="trends-analysis-toolbar">
  {#if showRangeControl}
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
  {:else}
    <div class="trends-toolbar__row trends-toolbar__row--range" data-testid="trends-sticky-toolbar">
      <!-- Keep sticky toolbar testid for layout/QA; range control intentionally omitted. -->
    </div>
  {/if}

  <div class="trends-toolbar__row" data-testid="trends-tabs-toolbar">
    <TabBar
      value={activeTab}
      options={tabOptions}
      ariaLabel={$_('trends.tabs.label')}
      testId="trends-tabs"
      on:change={(event) => dispatch('tabChange', { value: event.detail.value })}
    />
  </div>

  {#if showCompareFilters && embedCompareFilters}
    <div
      class="trends-toolbar__row trends-toolbar__row--filters"
      data-testid="trends-filters-toolbar"
    >
      <slot name="compare-filters" />
    </div>
  {/if}
</div>

<style>
  /* #703 Stage 2: the toolbar no longer owns sticky chrome — it renders inside
   * ScreenHeader's sticky `controls` slot, which provides blur/backdrop and the
   * top offset. Here it is just the control layout (range + tabs + filters). */
  .trends-toolbar {
    display: grid;
    gap: var(--screen-header-controls-gap, var(--space-2));
    min-width: 0;
  }

  .trends-toolbar__row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--screen-header-controls-gap, var(--space-2));
    min-width: 0;
  }

  .trends-toolbar__row--filters {
    padding-top: var(--screen-header-controls-pad, var(--space-1));
    border-top: 1px solid var(--color-border);
    transition:
      padding-top 0.2s ease,
      border-color 0.2s ease;
  }

  /* #786/#848: keep a light separator so densified rows do not visually merge. */
  :global(.screen-header--scrolled) .trends-toolbar__row--filters {
    border-top-color: color-mix(in srgb, var(--color-border) 55%, transparent);
  }

  @media (prefers-reduced-motion: reduce) {
    .trends-toolbar__row--filters {
      transition: none;
    }
  }

  @media (max-width: 480px) {
    .trends-toolbar {
      gap: var(--screen-header-controls-gap, var(--space-1));
    }

    .trends-toolbar__row {
      gap: var(--screen-header-controls-gap, var(--space-2));
    }
  }
</style>
