<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { TAG_CATEGORIES, type TagCategory } from '$lib/api/tags';

  export let selectedCategory: TagCategory | 'all' = 'all';

  const dispatch = createEventDispatcher<{
    categoryChange: { category: TagCategory | 'all' };
    openSettings: void;
  }>();
</script>

<div class="quick-filters" data-testid="trends-compare-quick-filters">
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

  :global(.screen-header--scrolled) .quick-filters {
    flex-wrap: nowrap;
    overflow: hidden;
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
