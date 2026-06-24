<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import InsightCard from './InsightCard.svelte';
  import InsightStageHeader from './InsightStageHeader.svelte';

  export let insight: InsightResponse;
  export let maturity: InsightMaturity | null = null;
  export let entryCount = 0;
  export let inactiveTagIds: readonly string[] = [];
  export let showMilestone = false;

  const dispatch = createEventDispatcher<{ dismissMilestone: { key: string } }>();
</script>

<section class="mobile-lead" data-testid="mobile-insight-lead">
  <header class="mobile-lead__header">
    <p class="mobile-lead__eyebrow">{$_('insights.mobile.eyebrow')}</p>
    <h2>{$_('insights.mobile.strongest_heading')}</h2>
    <p>{$_('insights.mobile.context', { values: { days: 90, n: entryCount } })}</p>
  </header>

  <InsightCard {insight} {maturity} {inactiveTagIds} featured showConfidenceSummary />

  <p class="mobile-lead__note" data-testid="mobile-insight-correlation-note">
    {$_('insights.mobile.correlation_note')}
    <a href="/insights/disclaimer">{$_('insights.mobile.correlation_link')}</a>
  </p>

  {#if maturity}
    <div class="mobile-lead__maturity" data-testid="mobile-insight-maturity">
      <p class="mobile-lead__section-label">{$_('insights.mobile.maturity_heading')}</p>
      <InsightStageHeader
        {maturity}
        {showMilestone}
        on:dismissMilestone={(event) => dispatch('dismissMilestone', event.detail)}
      />
    </div>
  {/if}
</section>

<style>
  .mobile-lead {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .mobile-lead__header,
  .mobile-lead__header h2,
  .mobile-lead__header p,
  .mobile-lead__note,
  .mobile-lead__section-label {
    margin: 0;
  }

  .mobile-lead__header {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .mobile-lead__eyebrow,
  .mobile-lead__section-label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .mobile-lead__header h2 {
    font-size: var(--text-xl);
    line-height: 1.25;
  }

  .mobile-lead__header > p:last-child,
  .mobile-lead__note {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .mobile-lead__note {
    padding: 0 var(--space-1);
  }

  .mobile-lead__note a {
    color: var(--color-primary);
    font-weight: 700;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .mobile-lead__maturity {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
</style>
