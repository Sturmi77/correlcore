<script lang="ts">
  /**
   * InsightHistoryTimeline — #601 Phase 2
   *
   * Groups history rows by generated_for_date. Shows active + dismissed
   * versions with a past-evaluation label and subject evolution meta.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightHistoryItem, InsightHistoryVisibility } from '$lib/api/insights';
  import InsightCard from './InsightCard.svelte';
  import TabBar from '$lib/components/common/TabBar.svelte';

  export let items: InsightHistoryItem[] = [];
  export let status: InsightHistoryVisibility = 'all';
  export let loading = false;
  export let error: string | null = null;
  export let total = 0;

  const dispatch = createEventDispatcher<{
    statusChange: { status: InsightHistoryVisibility };
    loadMore: void;
  }>();

  $: filterOptions = [
    { id: 'all', label: $_('insights.history.filter_all') },
    { id: 'active', label: $_('insights.history.filter_active') },
    { id: 'dismissed', label: $_('insights.history.filter_dismissed') },
  ];

  $: groups = groupByDate(items);

  function groupByDate(
    rows: InsightHistoryItem[]
  ): { date: string; items: InsightHistoryItem[] }[] {
    const map = new Map<string, InsightHistoryItem[]>();
    for (const row of rows) {
      const key = row.generated_for_date;
      const list = map.get(key) ?? [];
      list.push(row);
      map.set(key, list);
    }
    return [...map.entries()].map(([date, groupItems]) => ({ date, items: groupItems }));
  }

  function formatEvolution(item: InsightHistoryItem): string | null {
    if (!item.first_seen_on || !item.last_seen_on || !item.observation_count) return null;
    if (item.observation_count <= 1) return null;
    return $_('insights.history.evolution', {
      values: {
        first: item.first_seen_on,
        last: item.last_seen_on,
        count: item.observation_count,
      },
    });
  }
</script>

<section
  class="insight-history"
  data-testid="insight-history-timeline"
  aria-labelledby="insight-history-heading"
>
  <header class="insight-history__header">
    <h2 id="insight-history-heading">{$_('insights.history.heading')}</h2>
    <p>{$_('insights.history.hint')}</p>
  </header>

  <TabBar
    options={filterOptions}
    value={status}
    ariaLabel={$_('insights.history.filter_aria')}
    testId="history-tab-bar"
    on:change={(event) =>
      dispatch('statusChange', { status: event.detail.value as InsightHistoryVisibility })}
  />

  {#if loading && items.length === 0}
    <p class="insight-history__status">{$_('insights.history.loading')}</p>
  {:else if error}
    <p class="insight-history__status" role="alert">{error}</p>
  {:else if groups.length === 0}
    <p class="insight-history__status">{$_('insights.history.empty')}</p>
  {:else}
    <ol class="insight-history__days">
      {#each groups as group (group.date)}
        <li class="insight-history__day">
          <h3 class="insight-history__day-label">
            {$_('insights.history.day_heading', { values: { date: group.date } })}
          </h3>
          <ul class="insight-history__list">
            {#each group.items as item (item.id)}
              <li class="insight-history__item">
                <p class="insight-history__meta">
                  <span class="insight-history__badge" data-visibility={item.visibility}>
                    {item.visibility === 'dismissed'
                      ? $_('insights.history.badge_dismissed')
                      : $_('insights.history.badge_past')}
                  </span>
                  {#if formatEvolution(item)}
                    <span class="insight-history__evolution">{formatEvolution(item)}</span>
                  {/if}
                </p>
                <InsightCard insight={item} dismissable={false} showMaturityBadge={false} />
              </li>
            {/each}
          </ul>
        </li>
      {/each}
    </ol>

    {#if items.length < total}
      <button
        type="button"
        class="insight-history__more"
        data-testid="insight-history-load-more"
        disabled={loading}
        on:click={() => dispatch('loadMore')}
      >
        {loading ? $_('insights.history.loading') : $_('insights.history.load_more')}
      </button>
    {/if}
  {/if}
</section>

<style>
  .insight-history {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .insight-history__header {
    display: grid;
    gap: var(--space-1);
  }

  .insight-history__header h2,
  .insight-history__header p,
  .insight-history__status,
  .insight-history__day-label,
  .insight-history__meta,
  .insight-history__evolution {
    margin: 0;
  }

  .insight-history__header h2 {
    font-size: var(--text-lg);
  }

  .insight-history__header p,
  .insight-history__status,
  .insight-history__evolution {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .insight-history__days,
  .insight-history__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .insight-history__day {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .insight-history__day-label {
    font-size: var(--text-base);
    font-weight: 600;
  }

  .insight-history__item {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .insight-history__meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    align-items: center;
    font-size: var(--text-sm);
  }

  .insight-history__badge {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0.1rem 0.45rem;
    font-size: var(--text-xs);
  }

  .insight-history__badge[data-visibility='dismissed'] {
    color: var(--color-text-muted);
  }

  .insight-history__more {
    align-self: flex-start;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-text);
    font: inherit;
    font-size: var(--text-sm);
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
  }

  .insight-history__more:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
