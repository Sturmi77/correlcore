<script lang="ts">
  /**
   * InsightFeed — Issue #164, FRONTEND.md §5 Screen 3
   *
   * Renders a sorted, filterable list of InsightCards.
   * Sort: confidence × |effect_size| descending.
   * Filter tabs: All | Mood | Symptoms | Sleep
   *
   * Props
   * -----
   * insights    InsightResponse[]  All loaded insights
   * loading     boolean            Show skeleton cards
   * error       string | null      Inline error banner
   * entryCount  number             Total entries in last 90 days (for header)
   *
   * Events
   * ------
   * retry  Dispatched when user clicks the retry button in error state
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import EmptyState from '$lib/components/common/EmptyState.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import TabBar, { type TabBarOption } from '$lib/components/common/TabBar.svelte';
  import InsightCard from './InsightCard.svelte';
  import CorrelationDisclaimer from './CorrelationDisclaimer.svelte';

  export let insights: InsightResponse[] = [];
  export let maturity: InsightMaturity | null = null;
  export let loading = false;
  export let error: string | null = null;
  export let entryCount = 0;
  export let inactiveTagIds: readonly string[] = [];

  const dispatch = createEventDispatcher<{ retry: void }>();

  type FilterTab = 'all' | 'mood' | 'symptoms' | 'sleep';
  let activeTab: FilterTab = 'all';
  let disclaimerOpen = false;

  const TABS: { id: FilterTab; label: string }[] = [
    { id: 'all', label: 'insights.feed.tab_all' },
    { id: 'mood', label: 'insights.feed.tab_mood' },
    { id: 'symptoms', label: 'insights.feed.tab_symptoms' },
    { id: 'sleep', label: 'insights.feed.tab_sleep' },
  ];

  const METRIC_MAP: Record<FilterTab, string[]> = {
    all: [],
    mood: ['mood'],
    symptoms: ['symptom', 'symptoms'],
    sleep: ['sleep'],
  };

  function score(i: InsightResponse): number {
    return (i.confidence ?? 0) * Math.abs(i.effect_size ?? 0);
  }

  $: filtered = insights
    .filter((i) => {
      if (activeTab === 'all') return true;
      const keywords = METRIC_MAP[activeTab];
      return keywords.some((k) => i.metric?.toLowerCase().includes(k));
    })
    .sort((a, b) => score(b) - score(a));
  $: isPhaseEmpty = Boolean(maturity && insights.length === 0);
  $: emptyTitleKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.title`
    : 'insights.feed.empty_title';
  $: emptyBodyKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.body`
    : 'insights.feed.empty_body';
  $: filterTabOptions = TABS.map(
    (tab): TabBarOption => ({
      id: tab.id,
      label: $_(tab.label),
      testId: `insight-feed-tab-${tab.id}`,
    })
  );

  const SKELETON_COUNT = 3;
  const skeletonItems: number[] = Array.from({ length: SKELETON_COUNT }, (_, idx) => idx);
</script>

<section class="if-feed" aria-label={$_('insights.feed.aria_label')} data-testid="insight-feed">
  <!-- Header -->
  <header class="if-header">
    <div class="if-header__left">
      <h1 class="if-title" data-testid="insight-feed-title">
        {$_('insights.feed.title')}
      </h1>
      <p class="if-subtitle" data-testid="insight-feed-subtitle">
        {$_('insights.feed.subtitle', { values: { days: 90, n: entryCount } })}
      </p>
    </div>
    <button
      class="if-disclaimer-btn"
      aria-label={$_('insights.feed.disclaimer_aria')}
      data-testid="insight-feed-disclaimer-btn"
      on:click={() => (disclaimerOpen = true)}
    >
      <svg
        width="18"
        height="18"
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
  </header>

  <!-- Filter tabs -->
  <TabBar
    value={activeTab}
    options={filterTabOptions}
    ariaLabel={$_('insights.feed.filter_label')}
    testId="insight-feed-tabs"
    on:change={(event) => (activeTab = event.detail.value as FilterTab)}
  />

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
      actionHref="/"
      testId="insight-feed-empty"
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
      {#each filtered as insight (insight.id)}
        <li>
          <InsightCard {insight} {maturity} {inactiveTagIds} />
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
    gap: var(--space-4);
  }

  .if-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .if-header__left {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .if-title {
    font-size: var(--text-xl);
    font-weight: 700;
    margin: 0;
    color: var(--color-text);
  }

  .if-subtitle {
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
    gap: var(--space-3);
  }
</style>
