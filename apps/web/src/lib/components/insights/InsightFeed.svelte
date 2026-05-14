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
  import type { InsightResponse } from '$lib/api/insights';
  import InsightCard from './InsightCard.svelte';
  import CorrelationDisclaimer from './CorrelationDisclaimer.svelte';

  export let insights: InsightResponse[] = [];
  export let loading = false;
  export let error: string | null = null;
  export let entryCount = 0;

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
  <div
    class="if-tabs"
    role="tablist"
    aria-label={$_('insights.feed.filter_label')}
    data-testid="insight-feed-tabs"
  >
    {#each TABS as tab}
      <button
        role="tab"
        aria-selected={activeTab === tab.id}
        class="if-tab"
        class:if-tab--active={activeTab === tab.id}
        data-testid="insight-feed-tab-{tab.id}"
        on:click={() => (activeTab = tab.id)}
      >
        {$_(tab.label)}
      </button>
    {/each}
  </div>

  <!-- Inline error banner -->
  {#if error}
    <div class="if-error" role="alert" data-testid="insight-feed-error">
      <span>{error}</span>
      <button
        class="if-error__retry"
        data-testid="insight-feed-retry"
        on:click={() => dispatch('retry')}
      >
        {$_('entry.autosave.retry')}
      </button>
    </div>
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
    <div class="if-empty" data-testid="insight-feed-empty">
      <svg
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
      <p>{$_('insights.feed.empty_title')}</p>
      <span>{$_('insights.feed.empty_body')}</span>
      <a href="/" class="if-empty__cta">{$_('insights.feed.empty_cta')}</a>
    </div>

    <!-- Feed -->
  {:else if !error}
    <ul class="if-list" data-testid="insight-feed-list">
      {#each filtered as insight (insight.id)}
        <li>
          <InsightCard {insight} />
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

  .if-tabs {
    display: flex;
    gap: var(--space-1);
    flex-wrap: wrap;
  }

  .if-tab {
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--color-text-muted);
    border: 1px solid transparent;
    transition:
      color var(--transition-interactive),
      background var(--transition-interactive),
      border-color var(--transition-interactive);
  }

  .if-tab:hover {
    color: var(--color-text);
    background: var(--color-surface-offset);
  }

  .if-tab--active {
    color: var(--color-primary);
    background: var(--color-primary-highlight);
    border-color: oklch(from var(--color-primary) l c h / 0.25);
  }

  .if-error {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-error-highlight);
    border: 1px solid oklch(from var(--color-error) l c h / 0.25);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    color: var(--color-error);
  }

  .if-error__retry {
    flex-shrink: 0;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-error);
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .if-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .if-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--space-3);
    padding: var(--space-16) var(--space-8);
    color: var(--color-text-muted);
  }

  .if-empty p {
    font-size: var(--text-base);
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  .if-empty span {
    font-size: var(--text-sm);
    max-width: 36ch;
    margin: 0;
  }

  .if-empty__cta {
    margin-top: var(--space-2);
    padding: var(--space-2) var(--space-5);
    background: var(--color-primary);
    color: var(--color-text-inverse);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 600;
    text-decoration: none;
    transition: background var(--transition-interactive);
  }

  .if-empty__cta:hover,
  .if-empty__cta:focus-visible {
    background: var(--color-primary-hover);
  }
</style>
