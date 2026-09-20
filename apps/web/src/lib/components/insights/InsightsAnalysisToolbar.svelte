<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import type { TrendWindowDays } from '$lib/utils/trendWindowDays';

  export let analysisRange: TrendWindowDays | number;
  export let analysisRangeOptions: SegmentedControlOption[] = [];

  const dispatch = createEventDispatcher<{
    rangeChange: { value: string };
  }>();
</script>

<div class="insights-toolbar" data-testid="insights-analysis-toolbar">
  <div class="insights-toolbar__row" data-testid="insights-sticky-toolbar">
    <SegmentedControl
      value={String(analysisRange)}
      options={analysisRangeOptions}
      ariaLabel={$_('insights.page.analysis_range_label')}
      testId="insights-range-control"
      on:change={(event) => dispatch('rangeChange', { value: event.detail.value })}
    />
  </div>
</div>

<style>
  /* #703 Stage 2: the toolbar renders inside ScreenHeader's sticky `controls`
   * slot, which owns the blur/backdrop chrome — here it is just the layout. */
  .insights-toolbar {
    display: grid;
    gap: var(--screen-header-controls-gap, var(--space-2));
    min-width: 0;
  }

  .insights-toolbar__row {
    display: flex;
    align-items: center;
    gap: var(--screen-header-controls-gap, var(--space-3));
    min-width: 0;
  }

  @media (max-width: 480px) {
    .insights-toolbar {
      gap: var(--screen-header-controls-gap, var(--space-1));
    }

    .insights-toolbar__row {
      flex-wrap: wrap;
      gap: var(--screen-header-controls-gap, var(--space-2));
    }
  }
</style>
