<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import InsightCard from './InsightCard.svelte';
  import InsightStageHeader from './InsightStageHeader.svelte';

  import AnalysisCrossLink from '$lib/components/analysis/AnalysisCrossLink.svelte';

  export let insight: InsightResponse;
  export let maturity: InsightMaturity | null = null;
  export let entryCount = 0;
  export let inactiveTagIds: readonly string[] = [];
  export let showMilestone = false;
  /** Enables Explore aligned events on the lead insight card. */
  export let enableExploreEvents = false;

  const dispatch = createEventDispatcher<{
    dismiss: { id: string };
    dismissMilestone: { key: string };
    exploreEvents: { id: string };
  }>();
</script>

<section class="mobile-lead" data-testid="mobile-insight-lead">
  <header class="mobile-lead__header">
    <p class="mobile-lead__eyebrow">{$_('insights.mobile.eyebrow')}</p>
    <h2>{$_('insights.mobile.strongest_heading')}</h2>
    <p>{$_('insights.mobile.context', { values: { days: 90, n: entryCount } })}</p>
  </header>

  <InsightCard
    {insight}
    {maturity}
    {inactiveTagIds}
    featured
    showConfidenceSummary
    {enableExploreEvents}
    on:dismiss={(event) => dispatch('dismiss', event.detail)}
    on:exploreEvents={(event) => dispatch('exploreEvents', event.detail)}
  />

  <AnalysisCrossLink {insight} direction="to-trends" />

  {#if showMilestone && maturity}
    <div data-testid="mobile-insight-maturity">
      <InsightStageHeader
        {maturity}
        {showMilestone}
        milestoneOnly
        on:dismissMilestone={(event) => dispatch('dismissMilestone', event.detail)}
      />
    </div>
  {/if}
</section>

<style>
  .mobile-lead {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap-tight);
  }

  .mobile-lead__header,
  .mobile-lead__header h2,
  .mobile-lead__header p {
    margin: 0;
  }

  .mobile-lead__header {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .mobile-lead__eyebrow {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .mobile-lead__header h2 {
    font-size: var(--text-lg);
    line-height: 1.25;
  }

  .mobile-lead__header > p:last-child {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }
</style>
