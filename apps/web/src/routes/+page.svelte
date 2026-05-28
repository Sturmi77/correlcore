<script lang="ts">
  /**
   * Home route — ADR-0017 Screen 1 (M3.5 Sprint 4).
   *
   * Authenticated home uses exactly three information zones:
   *   1. Today context (date, work context, entry status)
   *   2. Latest insight OR first-week banner (best-effort)
   *   3. 7-day mood sparkline + primary entry CTA
   *
   * Insight load never blocks the CTA. No matrix, summary grid, or
   * recent-entries list on Home — those live under Trends / Insights.
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, currentUser } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchDashboardSummary, type DashboardSummaryResponse } from '$lib/api/dashboard';
  import { insightStore, rankedInsights, loadInsights, dismissInsight } from '$lib/stores/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { mockDashboardSummary, mockEntries, mockUserPreferences } from '$lib/dev/mockEntries';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { findEntryForDate, localIsoDate } from '$lib/utils/home';
  import { shiftIsoDate } from '$lib/utils/streak';
  import Button from '$lib/components/common/Button.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import FirstWeekInsightBanner from '$lib/components/home/FirstWeekInsightBanner.svelte';
  import HomeSparkline from '$lib/components/home/HomeSparkline.svelte';
  import HomeTodayContext from '$lib/components/home/HomeTodayContext.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';
  import EntrySheet from '$lib/components/entries/EntrySheet.svelte';

  const HOME_SPARKLINE_DAYS = 7;
  const FIRST_WEEK_PATTERN_KEY = 'first_week_pattern';

  const todayIso = localIsoDate(new Date());

  let todayEntry: EntryResponse | null = null;
  let recentEntries: EntryResponse[] = [];
  let dashboardSummary: DashboardSummaryResponse | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let dashboardLoading = false;
  let dashboardLoaded = false;
  let entrySheetOpen = false;
  let entrySheetDate = todayIso;

  $: latestInsight = $insightStore.latest;
  $: insightMaturity = $insightStore.insightMaturity;
  $: insightLoading = $insightStore.loading;
  $: insightError = $insightStore.error ?? '';
  $: weekdayInsight = $rankedInsights.find((i) => i.insight_type === 'weekday_pattern') ?? null;
  $: firstWeekDismissed =
    userPreferences?.dismissed_insight_keys.includes(FIRST_WEEK_PATTERN_KEY) ?? false;
  $: showFirstWeekBanner = Boolean(weekdayInsight && !firstWeekDismissed);

  function openEntrySheet(date: string = todayIso) {
    entrySheetDate = date;
    entrySheetOpen = true;
  }

  function onEntrySheetSaved() {
    void loadDashboard();
    void loadInsights();
  }

  async function loadDashboard(): Promise<void> {
    dashboardLoading = true;
    try {
      if ($devForceVisualizations) {
        recentEntries = mockEntries.slice(0, HOME_SPARKLINE_DAYS);
        todayEntry = findEntryForDate(recentEntries, todayIso);
        dashboardSummary = mockDashboardSummary;
        userPreferences = mockUserPreferences;
        return;
      }

      const start = shiftIsoDate(todayIso, -(HOME_SPARKLINE_DAYS - 1));
      const [entriesResult, summaryResult, preferencesResult] = await Promise.allSettled([
        listEntries({ start_date: start, end_date: todayIso }),
        fetchDashboardSummary(todayIso),
        fetchUserPreferences(),
      ]);

      if (entriesResult.status === 'rejected') throw entriesResult.reason;

      recentEntries = entriesResult.value;
      todayEntry = findEntryForDate(recentEntries, todayIso);
      dashboardSummary = summaryResult.status === 'fulfilled' ? summaryResult.value : null;
      userPreferences = preferencesResult.status === 'fulfilled' ? preferencesResult.value : null;
    } catch {
      recentEntries = [];
      todayEntry = null;
      dashboardSummary = null;
      userPreferences = null;
    } finally {
      dashboardLoading = false;
      dashboardLoaded = true;
    }
  }

  $: if ($auth.status === 'authenticated' && !dashboardLoaded && !dashboardLoading) {
    void loadDashboard();
    void loadInsights();
  }

  $: if (
    dashboardLoaded &&
    $auth.status === 'authenticated' &&
    dashboardSummary?.entry_count === 0 &&
    userPreferences &&
    !userPreferences.onboarding_retro_completed
  ) {
    void goto('/onboarding/retro', { replaceState: true });
  }

  async function dismissFirstWeekBanner(): Promise<void> {
    const dismissed = new Set(userPreferences?.dismissed_insight_keys ?? []);
    dismissed.add(FIRST_WEEK_PATTERN_KEY);
    const optimistic = {
      ...(userPreferences ?? {
        user_id: $currentUser?.id ?? '',
        analytics_enabled: true,
        onboarding_retro_completed: false,
        onboarding_profile_completed: false,
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
      dismissed_insight_keys: [...dismissed],
    };
    userPreferences = optimistic;
    try {
      userPreferences = await updateUserPreferences({
        dismissed_insight_keys: optimistic.dismissed_insight_keys,
      });
    } catch {
      // Optimistic dismissal for this session.
    }
  }

  onMount(() => {
    if ($auth.status === 'authenticated' && !dashboardLoaded) {
      void loadDashboard();
      void loadInsights();
    }
  });
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

{#if $auth.status === 'authenticated'}
  <div class="home-screen">
    <!-- Zone 1: date + work context + entry status -->
    <section class="home-zone" data-testid="home-zone-context">
      <HomeTodayContext {todayIso} {todayEntry} loading={dashboardLoading && !dashboardLoaded} />
    </section>

    <!-- Zone 2: insight preview (best-effort) -->
    <section class="home-zone" data-testid="home-zone-insight">
      {#if showFirstWeekBanner}
        <FirstWeekInsightBanner on:dismiss={dismissFirstWeekBanner} />
      {:else}
        <InsightCard
          insight={latestInsight}
          maturity={insightMaturity}
          loading={insightLoading && !latestInsight}
          error={insightError}
          on:dismiss={(e) => void dismissInsight(e.detail.id)}
          on:retry={() => void loadInsights()}
        />
      {/if}
    </section>

    <!-- Zone 3: sparkline + primary CTA -->
    <section class="home-zone home-zone--foot" data-testid="home-zone-sparkline-cta">
      <HomeSparkline
        entries={recentEntries}
        {todayIso}
        days={HOME_SPARKLINE_DAYS}
        loading={dashboardLoading && !dashboardLoaded}
      />

      <Button
        type="button"
        variant="primary"
        size="lg"
        fullWidth
        stacked
        className="home-cta"
        data-testid="home-cta"
        on:click={() => openEntrySheet(todayIso)}
      >
        {#if todayEntry}
          <span class="text-lg font-semibold">{$_('home.cta_edit_entry')}</span>
        {:else}
          <span class="text-lg font-semibold">{$_('home.cta_log_today')}</span>
        {/if}
        <span class="text-sm home-cta__hint">{$_('entry.subtitle')}</span>
      </Button>
    </section>

    <EntrySheet
      bind:open={entrySheetOpen}
      initialDate={entrySheetDate}
      on:saved={onEntrySheetSaved}
    />
  </div>
{:else}
  <div class="flex flex-col items-center justify-center gap-8 min-h-[80dvh]">
    <div class="flex flex-col items-center gap-4">
      <svg
        aria-label="CorrelCore"
        viewBox="0 0 48 48"
        width="64"
        height="64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="3" opacity="0.2" />
        <path
          d="M24 4 A20 20 0 0 1 44 24"
          stroke="var(--color-primary)"
          stroke-width="3"
          stroke-linecap="round"
        />
        <path
          d="M16 26 Q24 34 32 26"
          stroke="var(--color-primary)"
          stroke-width="2.5"
          stroke-linecap="round"
          fill="none"
        />
        <circle cx="19" cy="20" r="1.5" fill="var(--color-primary)" />
        <circle cx="29" cy="20" r="1.5" fill="var(--color-primary)" />
      </svg>

      <h1 class="h1 text-center" style="font-size: var(--text-xl)">
        {$_('app.name')}
      </h1>
      <p class="text-center" style="font-size: var(--text-base); color: var(--color-text-muted)">
        {$_('app.tagline')}
      </p>
    </div>

    <div class="flex items-center gap-3">
      <span style="font-size: var(--text-sm); color: var(--color-text-muted)"
        >{$_('theme.label')}</span
      >
      <ThemeToggle testId="landing-theme-toggle" />
    </div>

    <div
      class="badge"
      style="
        background: color-mix(in srgb, var(--color-warning) 15%, transparent);
        color: var(--color-warning);
        font-size: var(--text-xs);
      "
    >
      Pre-Alpha — M0 Setup
    </div>
  </div>
{/if}

<style>
  .home-screen {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
    padding-top: var(--space-4);
    padding-bottom: var(--space-8);
  }

  .home-zone {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .home-zone--foot {
    gap: var(--space-5);
  }

  :global(.home-cta) {
    border: 1px solid color-mix(in oklch, var(--color-primary) 25%, transparent);
  }

  :global(.home-cta .home-cta__hint) {
    color: color-mix(in srgb, var(--color-text-inverse) 78%, transparent);
  }
</style>
