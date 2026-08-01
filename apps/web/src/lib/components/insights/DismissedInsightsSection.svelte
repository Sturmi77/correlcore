<script lang="ts">
  /**
   * DismissedInsightsSection — #601 Phase 0/1
   *
   * Lists hide'd insights with Undo. Collapsed by default so the archive
   * does not consume feed-height. Cards are not dismissable here; primary
   * action is "Show again".
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
  <details class="dismissed-insights" data-testid="dismissed-insights-section">
    <summary
      class="dismissed-insights__summary"
      data-testid="dismissed-insights-toggle"
      aria-label={$_('insights.dismissed.toggle_aria', {
        values: { count: resolvedItems.length },
      })}
    >
      <span class="dismissed-insights__summary-title" id="dismissed-insights-heading">
        {$_('insights.dismissed.heading')}
      </span>
      <span class="dismissed-insights__count">{resolvedItems.length}</span>
    </summary>

    <p class="dismissed-insights__hint">{$_('insights.dismissed.hint')}</p>

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
  </details>
{/if}

<style>
  .dismissed-insights {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    padding: var(--space-3);
  }

  .dismissed-insights__summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    cursor: pointer;
    list-style: none;
    font: inherit;
    color: inherit;
  }

  .dismissed-insights__summary::-webkit-details-marker {
    display: none;
  }

  .dismissed-insights__summary::after {
    content: '';
    width: 0.55rem;
    height: 0.55rem;
    border-right: 2px solid var(--color-text-muted);
    border-bottom: 2px solid var(--color-text-muted);
    transform: rotate(45deg);
    transition: transform 120ms ease;
    flex-shrink: 0;
  }

  .dismissed-insights[open] .dismissed-insights__summary::after {
    transform: rotate(225deg);
    margin-top: 0.25rem;
  }

  .dismissed-insights__summary-title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .dismissed-insights__count {
    margin-left: auto;
    min-width: 1.5rem;
    padding: 0.1rem 0.45rem;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-text-muted) 12%, var(--color-surface));
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    text-align: center;
  }

  .dismissed-insights__hint {
    margin: 0;
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
