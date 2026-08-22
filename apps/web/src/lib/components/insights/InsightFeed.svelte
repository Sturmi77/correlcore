<script lang="ts">
  /**
   * InsightFeed — Issue #164, FRONTEND.md §5 Screen 3
   *
   * Renders a sorted list of InsightCards.
   * Sort: confidence × |effect_size| descending.
   *
   * Props
   * -----
   * insights           InsightResponse[]  Insights for the current view
   * totalInsightCount  number             Total API insight count for empty-state semantics
   * dismissedCount     number             Insights the user has dismissed (empty-state semantics)
   * loading            boolean            Show skeleton cards
   * error              string | null      Inline error banner
   * entryCount         number             Total entries in analysis window (for header)
   * staleAfterHours               number             #755: hours since the latest successful run
   *                                                   before the feed is flagged stale (default 40)
   * stalenessInsights             InsightResponse[]  Full page set used for freshness calculation
   * lastSuccessfulInsightRunAt    Date | string      Successful run timestamp, including zero-result runs
   * analyticsEnabled              boolean            Suppresses remediation when analytics is disabled
   * now                           Date | string      Injectable "current time" for staleness checks
   *
   * Events
   * ------
   * retry       Dispatched when user clicks the retry button in error state
   * regenerate  Dispatched when user clicks refresh-insights in the true-empty state, or the
   *             regenerate action in the staleness banner (#755)
   */
  import { createEventDispatcher, onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import EmptyState from '$lib/components/common/EmptyState.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import InsightCard from './InsightCard.svelte';
  import CorrelationDisclaimer from './CorrelationDisclaimer.svelte';
  import { OPEN_ENTRY_HOME_PATH } from '$lib/navigation/openEntry';
  import { rankInsights } from '$lib/utils/insightRanking';

  export let insights: InsightResponse[] = [];
  /** Unfiltered count from the parent; defaults to `insights.length` for standalone use. */
  export let totalInsightCount: number | undefined = undefined;
  export let maturity: InsightMaturity | null = null;
  export let loading = false;
  export let error: string | null = null;
  export let entryCount = 0;
  /** Entries with notes in the analysis window — drives the note soft prompt. */
  export let notedEntryCount: number | null = null;
  export let inactiveTagIds: readonly string[] = [];
  export let showContext = true;
  /** When false, cards omit phase badges because maturity is shown in page chrome (O-01). */
  export let showMaturityBadge = true;
  /** Count of dismissed insights, to distinguish "all dismissed" from "none yet" (#686). */
  export let dismissedCount = 0;
  /** Analysis window in days for the context subtitle (O-46). */
  export let analysisRangeDays = 90;
  /** Enables the Explore aligned events affordance on insight cards (ADR-0035 §6). */
  export let enableExploreEvents = false;
  export let regenerateBusy = false;
  export let regenerateMessage = '';
  export let regenerateError = '';
  /**
   * #755 (Staleness-UX): hours since the latest insight's `generated_at`
   * after which the feed is considered stale (nightly worker run missed).
   * Default 40h sits inside the recommended 36-48h window — long enough to
   * absorb a single delayed run, short enough to flag a genuinely missed one.
   */
  export let staleAfterHours = 40;
  /** Full page set; may include a primary mobile card rendered outside this feed. */
  export let stalenessInsights: readonly InsightResponse[] | undefined = undefined;
  /** Successful worker/on-demand generation timestamp, including zero-candidate runs. */
  export let lastSuccessfulInsightRunAt: Date | string | null = null;
  /** Generation is intentionally unavailable when analytics has been disabled. */
  export let analyticsEnabled = true;
  /** Injection seam for tests. Undefined keeps a live wall-clock value. */
  export let now: Date | string | undefined = undefined;
  /** Renders only status messages; used beside the compact primary mobile card. */
  export let hideContent = false;

  const dispatch = createEventDispatcher<{
    retry: void;
    regenerate: void;
    dismiss: { id: string };
    exploreEvents: { id: string };
    selectDate: { date: string };
  }>();

  let disclaimerOpen = false;
  let currentTime = new Date();

  onMount(() => {
    if (now !== undefined) return;

    const refreshClock = () => {
      currentTime = new Date();
    };
    const interval = window.setInterval(refreshClock, 5 * 60 * 1000);
    document.addEventListener('visibilitychange', refreshClock);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshClock);
    };
  });

  $: filtered = rankInsights(insights);
  $: resolvedTotalCount = totalInsightCount ?? insights.length;
  $: isPhaseEmpty = Boolean(maturity && resolvedTotalCount === 0);
  // #686: "all dismissed" is distinct from "no insights yet" — insights existed,
  // the user has just cleared them all, so the empty state says *new*.
  $: isAllDismissed = !isPhaseEmpty && resolvedTotalCount === 0 && dismissedCount > 0;
  $: emptyTitleKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.title`
    : isAllDismissed
      ? 'insights.feed.empty_all_dismissed_title'
      : 'insights.feed.empty_title';
  $: emptyBodyKey = isPhaseEmpty
    ? `insights.feed.empty_phase.${maturity?.phase}.body`
    : isAllDismissed
      ? 'insights.feed.empty_all_dismissed_body'
      : 'insights.feed.empty_body';
  // #755: compact layouts render the primary card outside this component.
  // Always inspect the full page set so that card participates in freshness.
  $: stalenessSource = stalenessInsights ?? insights;
  $: latestGeneratedAt = stalenessSource.reduce<string>(
    (latest, insight) => (insight.generated_at > latest ? insight.generated_at : latest),
    ''
  );
  // A successful run that produces zero candidates creates no Insight row.
  // Prefer the per-user worker-run signal and retain generated_at as a
  // compatibility fallback while older API versions are still deployed.
  $: freshnessReferenceAt = lastSuccessfulInsightRunAt ?? latestGeneratedAt;
  $: isStale =
    analyticsEnabled &&
    Boolean(freshnessReferenceAt) &&
    new Date(now ?? currentTime).getTime() - new Date(freshnessReferenceAt).getTime() >
      staleAfterHours * 60 * 60 * 1000;
  $: showRegenerateAction = analyticsEnabled && (isPhaseEmpty || isStale);
  $: showStaleBanner = isStale && !loading && !error;
  $: staleDateLabel = formatStaleDate(freshnessReferenceAt);
  // #632 review: do not claim "these are correlations" while loading/empty/error.
  $: showCorrelationHint = showContext && !loading && !error && resolvedTotalCount > 0;

  function formatStaleDate(value: Date | string | null): string {
    if (value === null) return '';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '';
    return new Intl.DateTimeFormat($locale ?? undefined, { dateStyle: 'medium' }).format(parsed);
  }

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
    {#if showCorrelationHint}
      <p class="if-correlation-hint" data-testid="insight-feed-correlation-hint">
        {$_('insights.feed.correlation_header')}
      </p>
    {/if}
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

  <!-- #755: staleness banner — insights exist but the nightly run appears to
       have been missed. Independent of the empty state; shown alongside the
       feed list whenever the latest insight is older than the threshold. -->
  {#if showStaleBanner}
    <InlineAlert
      variant="warning"
      message={$_('insights.feed.stale_banner_message', { values: { date: staleDateLabel } })}
      actionLabel={$_('insights.feed.stale_banner_action')}
      actionTestId="insight-feed-stale-action"
      actionLoading={regenerateBusy}
      actionDisabled={regenerateBusy}
      testId="insight-feed-stale-banner"
      on:action={() => dispatch('regenerate')}
    />
  {/if}

  {#if !hideContent && notedEntryCount !== null && notedEntryCount < 20}
    <p class="if-note-prompt" data-testid="insight-note-soft-prompt">
      {$_('insights.note_evidence.soft_prompt')}
    </p>
  {/if}

  {#if !hideContent}
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
              on:dismiss={(event) => dispatch('dismiss', event.detail)}
              on:exploreEvents={(event) => dispatch('exploreEvents', event.detail)}
              on:selectDate={(event) => dispatch('selectDate', event.detail)}
            />
          </li>
        {/each}
      </ul>
    {/if}
  {/if}

  <CorrelationDisclaimer open={disclaimerOpen} on:close={() => (disclaimerOpen = false)} />
</section>

<style>
  .if-feed {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap);
  }

  .if-note-prompt {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
    color: var(--color-text-muted);
    font-size: var(--text-sm);
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

  /* #632: single correlation hint for the whole feed (replaces the former
     per-statement "not a cause/diagnosis" tails). */
  .if-correlation-hint {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    margin: var(--space-1) 0 0;
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
