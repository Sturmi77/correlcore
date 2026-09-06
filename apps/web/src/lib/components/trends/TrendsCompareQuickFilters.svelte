<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { TAG_CATEGORIES, type TagCategory } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';

  export let metrics: Record<MetricKey, boolean>;
  export let selectedCategory: TagCategory | 'all' = 'all';

  const metricLabels: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
    sleep_quality_avg: 'trends.metric.sleep_quality',
  };

  const dispatch = createEventDispatcher<{
    metricToggle: { metric: MetricKey };
    categoryChange: { category: TagCategory | 'all' };
    openSettings: void;
  }>();
</script>

<div class="quick-filters" data-testid="trends-compare-quick-filters">
  <div class="quick-filters__metrics" role="group" aria-label={$_('trends.metrics_label')}>
    {#each Object.entries(metricLabels) as [key, label] (key)}
      <button
        type="button"
        class="quick-filters__chip"
        class:quick-filters__chip--active={metrics[key as MetricKey]}
        aria-pressed={metrics[key as MetricKey]}
        data-testid={`trends-quick-metric-${key}`}
        on:click={() => dispatch('metricToggle', { metric: key as MetricKey })}
      >
        {$_(label)}
      </button>
    {/each}
  </div>

  <label class="quick-filters__category">
    <span class="sr-only">{$_('trends.category')}</span>
    <select
      value={selectedCategory}
      data-testid="trends-quick-category"
      on:change={(event) =>
        dispatch('categoryChange', { category: event.currentTarget.value as TagCategory | 'all' })}
    >
      <option value="all">{$_('trends.category_all')}</option>
      {#each TAG_CATEGORIES as category}
        <option value={category}>{$_(`tag.category.${category}`)}</option>
      {/each}
    </select>
  </label>

  <button
    type="button"
    class="quick-filters__customize"
    data-testid="trends-compare-customize"
    on:click={() => dispatch('openSettings')}
  >
    {$_('trends.mobile.customize')}
  </button>
</div>

<style>
  .quick-filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--screen-header-controls-gap, var(--space-2));
    min-width: 0;
  }

  .quick-filters__metrics {
    display: inline-flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    min-width: 0;
    flex: 1 1 auto;
  }

  .quick-filters__chip {
    min-height: var(--screen-header-control-min-height, var(--tap-target));
    padding: 0 var(--space-2);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    cursor: pointer;
  }

  .quick-filters__chip--active {
    border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
    color: var(--color-primary);
  }

  .quick-filters__category {
    display: inline-flex;
    min-width: 0;
    flex: 0 1 8.5rem;
  }

  .quick-filters__category select {
    width: 100%;
    min-height: var(--screen-header-control-min-height, var(--tap-target));
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-2);
    background: var(--color-surface);
    color: inherit;
    font-size: var(--text-xs);
  }

  .quick-filters__customize {
    min-height: var(--screen-header-control-min-height, var(--tap-target));
    padding: 0 var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  /* #786/#848: scrolled sticky chrome — pin category + customize; only the
   * metric chip track scrolls horizontally so chips cannot paint over CTAs. */
  :global(.screen-header--scrolled) .quick-filters {
    flex-wrap: nowrap;
    overflow: hidden;
  }

  :global(.screen-header--scrolled) .quick-filters__metrics {
    flex: 1 1 auto;
    min-width: 0;
    flex-wrap: nowrap;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }

  :global(.screen-header--scrolled) .quick-filters__metrics::-webkit-scrollbar {
    display: none;
  }

  :global(.screen-header--scrolled) .quick-filters__chip {
    flex: 0 0 auto;
    padding-inline: var(--space-2);
  }

  :global(.screen-header--scrolled) .quick-filters__category,
  :global(.screen-header--scrolled) .quick-filters__customize {
    flex: 0 0 auto;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
