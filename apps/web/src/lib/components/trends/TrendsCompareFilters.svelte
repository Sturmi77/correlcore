<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { TAG_CATEGORIES, type TagCategory } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';
  import SegmentedControl from '$lib/components/common/SegmentedControl.svelte';

  export let smoothing = true;
  export let smoothingAvailable = false;
  export let metrics: Record<MetricKey, boolean>;
  export let selectedCategory: TagCategory | 'all' = 'all';

  const metricLabels: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
  };
  const dispatch = createEventDispatcher<{
    smoothingChange: { value: boolean };
    metricToggle: { metric: MetricKey };
    categoryChange: { category: TagCategory | 'all' };
  }>();

  $: smoothingOptions = [
    { id: 'raw', label: $_('trends.smoothing.raw'), testId: 'trends-smoothing-raw' },
    { id: 'smoothed', label: $_('trends.smoothing.smoothed'), testId: 'trends-smoothing-smoothed' },
  ];
</script>

<div class="compare-filters" data-testid="trends-compare-filters">
  {#if smoothingAvailable}
    <SegmentedControl
      value={smoothing ? 'smoothed' : 'raw'}
      options={smoothingOptions}
      ariaLabel={$_('trends.smoothing.label')}
      testId="trends-smoothing-control"
      on:change={(event) =>
        dispatch('smoothingChange', { value: event.detail.value === 'smoothed' })}
    />
  {/if}
  <fieldset class="compare-filters__metrics">
    <legend>{$_('trends.metrics_label')}</legend>
    {#each Object.entries(metricLabels) as [key, label]}
      <label>
        <input
          type="checkbox"
          checked={metrics[key as MetricKey]}
          on:change={() => dispatch('metricToggle', { metric: key as MetricKey })}
        />
        {$_(label)}
      </label>
    {/each}
  </fieldset>
  <label class="compare-filters__select">
    <span>{$_('trends.category')}</span>
    <select
      value={selectedCategory}
      on:change={(event) =>
        dispatch('categoryChange', { category: event.currentTarget.value as TagCategory | 'all' })}
    >
      <option value="all">{$_('trends.category_all')}</option>
      {#each TAG_CATEGORIES as category}
        <option value={category}>{$_(`tag.category.${category}`)}</option>
      {/each}
    </select>
  </label>
</div>

<style>
  .compare-filters,
  .compare-filters__metrics {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
  }

  .compare-filters__metrics {
    margin: 0;
    padding: 0;
    border: 0;
  }

  .compare-filters__metrics legend {
    width: 100%;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  .compare-filters__metrics label,
  .compare-filters__select {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
  }

  .compare-filters__select span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .compare-filters__select select {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-2);
    background: var(--color-surface);
    color: inherit;
  }

  @media (max-width: 767px) {
    .compare-filters,
    .compare-filters__metrics {
      align-items: stretch;
      flex-direction: column;
    }

    .compare-filters__metrics label,
    .compare-filters__select,
    .compare-filters__select select {
      width: 100%;
    }

    .compare-filters__select {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
