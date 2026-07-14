<script lang="ts">
  /**
   * InsightFeed — Issue #164, FRONTEND.md §5 Screen 3
   *
   * Renders a sorted, filterable list of InsightCards.
   * Sort: confidence × |effect_size| descending.
   * Filter tabs: All | Mood | Symptoms | Context
   *
   * Props
   * -----
   * insights           InsightResponse[]  Insights for the current view (may be pre-filtered)
   * totalInsightCount  number             Unfiltered API insight count for empty-state semantics
   * loading            boolean            Show skeleton cards
   * error              string | null      Inline error banner
   * entryCount         number             Total entries in analysis window (for header)
   *
   * Events
   * ------
   * retry       Dispatched when user clicks the retry button in error state
   * regenerate  Dispatched when user clicks refresh-insights in the true-empty state
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import EmptyState from '$lib/components/common/EmptyState.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import TabBar from '$lib/components/common/TabBar.svelte';
  import InsightCard from './InsightCard.svelte';
  import CorrelationDisclaimer from './CorrelationDisclaimer.svelte';
  import { OPEN_ENTRY_HOME_PATH } from '$lib/navigation/openEntry';
  import {
    filterInsightsByTab,
    getInsightFeedFilterTabs,
    type InsightFeedFilterTab,
  } from '$lib/utils/insightFeedFilter';
  import { rankInsights } from '$lib/utils/insightRanking';

  export let insights: InsightResponse[] = [];
  /** Unfiltered count from the parent; defaults to `insights.length` for standalone use. */
  export let totalInsightCount: number | undefined = undefined;
  export let maturity: InsightMaturity | null = null;
  export let loading = false;
  export let error: string | null = null;
  export let entryCount = 0;
  export let inactiveTagIds: readonly string[] = [];
  export let showContext = true;
  export let showFilters = true;
  /** When false, cards omit phase badges because maturity is shown in page chrome (O-01). */
  export let showMaturityBadge = true;
  /** When set, the parent owns filter UI and state (O-22). */
  export let filterTab: InsightFeedFilterTab | undefined = undefined;
  /** Analysis window in days for the context subtitle (O-46). */
  export let analysisRangeDays = 90;
  /** Enables the Explore aligned events affordance on insight cards (ADR-0035 §6). */
  export let enableExploreEvents = false;
  export let regenerateBusy = false;
  export let regenerateMessage = '';
  export let regenerateError = '';

  const dispatch = createEventDispatcher<{
    retry: void;
    regenerate: void;
    exploreEvents: { id: string };
  }>();

  let internalFilterTab: InsightFeedFilterTab = 'all';
  let disclaimerOpen = false;

  $: activeTab = filterTab ?? internalFilterTab;
  $: filterTabOptions = getInsightFeedFilterTabs($_, 'insight-feed-tab');

  $: filtered = rankInsights(filterInsightsByTab(insights, activeTab));
  $: resolvedTotalCount = totalInsightCount ?? insights.length;
  $: isPhaseEmpty = Boolean(maturity && resolvedTotalCount === 0);
  $: emptyTitleKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.title`
    : 'insights.feed.empty_title';
  $: emptyBodyKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.body`
    : 'insights.feed.empty_body';
  $: showRegenerateAction = isPhaseEmpty;

  const SKELETON_COUNT = 3;
  const skeletonItems: number[] = Array.from({ length: SKELETON_COUNT }, (_, idx) => idx);
</script>

<section class="if-feed" aria-label={$_('insights.feed.aria_label')} data-testid="insight-feed">
  {#if showContext}
    <div class="if-context-row">
      <p class="if-context" data-testid="insight-feed-context">
        {$_('insights.feed.subtitle', { values: { days: analysisRangeDays, n: entryCount } })}
      </p>
      <button
        class="if-disclaimer-btn"
        aria-label={$_('insights.feed.disclaimer_aria')}
        data-testid="insight-feed-disclaimer-btn"
        on:click={() => (disclaimerOpen = true)}
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
  {/if}

  {#if showFilters}
    <TabBar
      value={activeTab}
      options={filterTabOptions}
      ariaLabel={$_('insights.feed.filter_label')}
      testId="insight-feed-tabs"
      on:change={(event) => (internalFilterTab = event.detail.value as InsightFeedFilterTab)}
    />
  {/if}

  <!-- Inline error banner -->
  {#if error}
    <InlineAlert
      variant="error"
      message={error}
      actionLabel={$_('entry.autosave.retry')}
      actionTestId="insight-feed-retry"
      testId="insight-feed-error"
      on:action={() => dispatch('retry')}
    />
  {/if}

  {#if regenerateError}
    <InlineAlert variant="error" message={regenerateError} testId="insight-feed-regenerate-error" />
  {:else if regenerateMessage}
    <InlineAlert
      variant="success"
      message={regenerateMessage}
      testId="insight-feed-regenerate-success"
    />
  {/if}

  <!-- Loading skeleton -->
  {#if loading}
    <ul class="if-list" aria-busy="true" data-testid="insight-feed-skeleton">
      {#each skeletonItems as idx (idx)}
        <li>
          <InsightCard loading />
        </li>
      {/each}
    </ul>

    <!-- Empty state -->
  {:else if !error && filtered.length === 0}
    <EmptyState
      title={$_(emptyTitleKey)}
      body={$_(emptyBodyKey)}
      actionLabel={$_('insights.feed.empty_cta')}
      actionHref={OPEN_ENTRY_HOME_PATH}
      secondaryActionLabel={showRegenerateAction ? $_('insights.feed.empty_regenerate_cta') : ''}
      secondaryActionLoading={regenerateBusy}
      secondaryActionDisabled={regenerateBusy}
      compact
      testId="insight-feed-empty"
      on:secondaryAction={() => dispatch('regenerate')}
    >
      <svg
        slot="icon"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        aria-hidden="true"
      >
        <path d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2z" />
        <path d="M15 11v8a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v0" />
      </svg>
    </EmptyState>

    <!-- Feed -->
  {:else if !error}
    <ul class="if-list" data-testid="insight-feed-list">
      {#each filtered as insight, index (insight.id)}
        <li>
          <InsightCard
            {insight}
            {maturity}
            {inactiveTagIds}
            {showMaturityBadge}
            {enableExploreEvents}
            featured={index === 0}
            on:exploreEvents={(event) => dispatch('exploreEvents', event.detail)}
          />
        </li>
      {/each}
    </ul>
  {/if}

  <CorrelationDisclaimer open={disclaimerOpen} on:close={() => (disclaimerOpen = false)} />
</section>

<style>
  .if-feed {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap);
  }

  .if-context-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .if-context {
    flex: 1;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    margin: 0;
  }

  .if-disclaimer-btn {
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

  .if-disclaimer-btn:hover,
  .if-disclaimer-btn:focus-visible {
    color: var(--color-primary);
    background: var(--color-primary-highlight);
  }

  .if-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap-tight);
  }
</style>
