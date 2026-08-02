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
    openDisclaimer: void;
  }>();
</script>

<section class="mobile-lead" data-testid="mobile-insight-lead">
  <header class="mobile-lead__header">
    <div class="mobile-lead__eyebrow-row">
      <p class="mobile-lead__eyebrow">{$_('insights.mobile.eyebrow')}</p>
      <!--
        Canonical on-demand disclaimer entry point (#632 Phase-1). The lead
        replaces the InsightFeed header (which is rendered with
        showContext={false} alongside this component, or not rendered at
        all when there is only one insight) so it needs its own trigger —
        otherwise compact-width users would have no way to open the
        correlation disclaimer.
      -->
      <button
        type="button"
        class="mobile-lead__disclaimer-btn"
        aria-label={$_('insights.feed.disclaimer_aria')}
        data-testid="mobile-insight-lead-disclaimer-btn"
        on:click={() => dispatch('openDisclaimer')}
      >
        <svg
          style="width: var(--icon-md); height: var(--icon-md)"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </button>
    </div>
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

  .mobile-lead__eyebrow-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .mobile-lead__eyebrow {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .mobile-lead__disclaimer-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    transition:
      color var(--transition-interactive),
      background var(--transition-interactive);
  }

  .mobile-lead__disclaimer-btn:hover,
  .mobile-lead__disclaimer-btn:focus-visible {
    color: var(--color-primary);
    background: var(--color-primary-highlight);
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
