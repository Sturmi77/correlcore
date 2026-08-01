<script lang="ts">
  /**
   * DismissedInsightsSection — #601 Phase 0/1
   *
   * Lists hide'd insights with Undo. Cards are not dismissable here;
   * primary action is "Show again".
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import type { DismissedInsightItem } from './dismissedInsights';
  import InsightCard from './InsightCard.svelte';

  export let items: DismissedInsightItem[] = [];
  /** @deprecated Prefer `items`; kept for transitional call sites. */
  export let insights: InsightResponse[] = [];
  export let maturity: InsightMaturity | null = null;
  export let inactiveTagIds: readonly string[] = [];

  const dispatch = createEventDispatcher<{
    undismiss: { id: string; dismissalId: string };
  }>();

  $: resolvedItems =
    items.length > 0 ? items : insights.map((insight) => ({ dismissalId: insight.id, insight }));

  function titleFor(insight: InsightResponse): string {
    return insight.statement?.trim() || insight.subject_label || insight.metric || insight.id;
  }
</script>

{#if resolvedItems.length > 0}
  <section
    class="dismissed-insights"
    data-testid="dismissed-insights-section"
    aria-labelledby="dismissed-insights-heading"
  >
    <header class="dismissed-insights__header">
      <h2 id="dismissed-insights-heading">{$_('insights.dismissed.heading')}</h2>
      <p>{$_('insights.dismissed.hint')}</p>
    </header>

    <ul class="dismissed-insights__list">
      {#each resolvedItems as item (item.dismissalId)}
        <li class="dismissed-insights__item">
          <InsightCard
            insight={item.insight}
            {maturity}
            {inactiveTagIds}
            dismissable={false}
            showMaturityBadge={false}
          />
          <button
            type="button"
            class="dismissed-insights__undo"
            data-testid="dismissed-insight-undo"
            aria-label={$_('insights.dismissed.undo_aria', {
              values: { title: titleFor(item.insight) },
            })}
            on:click={() =>
              dispatch('undismiss', { id: item.insight.id, dismissalId: item.dismissalId })}
          >
            {$_('insights.dismissed.undo')}
          </button>
        </li>
      {/each}
    </ul>
  </section>
{/if}

<style>
  .dismissed-insights {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .dismissed-insights__header {
    display: grid;
    gap: var(--space-1);
  }

  .dismissed-insights__header h2,
  .dismissed-insights__header p {
    margin: 0;
  }

  .dismissed-insights__header h2 {
    font-size: var(--text-lg);
  }

  .dismissed-insights__header p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .dismissed-insights__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .dismissed-insights__item {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .dismissed-insights__undo {
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
</style>
