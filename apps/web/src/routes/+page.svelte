<script lang="ts">
  /**
   * Home route — ADR-0017 Screen 1 (M3.5 Sprint 4).
   *
   * Authenticated home uses exactly three information zones:
   *   1. Today context (date, work context, compact log/edit action)
   *   2. Daily Brief: latest insight summary OR phase fallback (brief-first)
   *   3. Primary entry CTA when today is not logged yet
   *
   * Insight load never blocks the CTA. No matrix, summary grid, or
   * recent-entries list on Home — those live under Trends / Insights.
   */

  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { auth, currentUser } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchDashboardSummary, type DashboardSummaryResponse } from '$lib/api/dashboard';
  import { insightStore, rankedInsights, loadInsights } from '$lib/stores/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
  import { pwaInstallStore } from '$lib/stores/pwaInstall';
  import { findEntryForDate, localIsoDate } from '$lib/utils/home';
  import { canUseOfflineSync } from '$lib/offline/featureFlag';
  import { findLocalEntryByDateSlot, localEntryToEntryResponse } from '$lib/stores/entriesOffline';
  import { isCalendarContextInsight } from '$lib/utils/insightConfounder';
  import { selectNewestWeekdayPattern } from '$lib/utils/homeWeekdayOverview';
  import { shiftIsoDate } from '$lib/utils/streak';
  import Button from '$lib/components/common/Button.svelte';
  import FirstWeekInsightBanner from '$lib/components/home/FirstWeekInsightBanner.svelte';
  import HomeTodayContext from '$lib/components/home/HomeTodayContext.svelte';
  import HomeDailyBrief from '$lib/components/home/HomeDailyBrief.svelte';
  import HomeWeekdayOverview from '$lib/components/home/HomeWeekdayOverview.svelte';
  import { entrySheetSaveSignal, entrySheetStore, openEntrySheet } from '$lib/stores/entrySheet';
  import { isOpenEntryRequested } from '$lib/navigation/openEntry';
  import { shouldShowOnboardingTags } from '$lib/utils/onboardingEntry';
  import LandingPage from '$lib/components/landing/LandingPage.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';

  const EARLY_CONTEXT_PATTERN_KEY = 'early_context_pattern';
  const LEGACY_FIRST_WEEK_PATTERN_KEY = 'first_week_pattern';

  const todayIso = localIsoDate(new Date());

  let todayEntry: EntryResponse | null = null;
  let recentEntries: EntryResponse[] = [];
  let dashboardSummary: DashboardSummaryResponse | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let dashboardLoading = false;
  let dashboardLoaded = false;
  let activeDevFixtureKey = '';
  let firstEntrySheetOpened = false;

  $: entrySheetOpen = $entrySheetStore.open;

  $: latestInsight = $insightStore.latest;
  $: insightMaturity = $insightStore.insightMaturity;
  $: insightLoading = $insightStore.loading;
  $: contextInsight = $rankedInsights.find((i) => isCalendarContextInsight(i)) ?? null;
  // See selectNewestWeekdayPattern's doc comment: rankInsights sorts by
  // confidence × |effect_size|, not recency, so picking the top-ranked
  // weekday_pattern match here could surface a stale weekday.
  $: weekdayInsight = selectNewestWeekdayPattern($rankedInsights);
  $: firstWeekDismissed =
    userPreferences?.dismissed_insight_keys.some((key) =>
      [EARLY_CONTEXT_PATTERN_KEY, LEGACY_FIRST_WEEK_PATTERN_KEY].includes(key)
    ) ?? false;
  $: showFirstWeekBanner = Boolean(contextInsight && !firstWeekDismissed);
  $: showOnboardingTags = shouldShowOnboardingTags(userPreferences, dashboardSummary?.entry_count);
  $: showPwaInstallBanner = Boolean(
    $pwaInstallStore.promptEvent &&
    !$pwaInstallStore.dismissed &&
    !$pwaInstallStore.installed &&
    ((dashboardSummary?.entry_count ?? 0) >= 1 || userPreferences?.onboarding_retro_completed)
  );

  function openEntry(date: string = todayIso): void {
    openEntrySheet(date, { onboardingTags: showOnboardingTags });
  }

  function devFixtureKey(): string {
    return `${$devPhase.presetId}:${$devPhase.entryCount}:${$devPhase.onboardingCompleted}`;
  }

  async function loadDashboard(): Promise<void> {
    dashboardLoading = true;
    try {
      if (get(devForceVisualizations)) {
        const fixture = getDevPhaseFixture($devPhase);
        activeDevFixtureKey = devFixtureKey();
        recentEntries = fixture.entries.slice(0, 7);
        todayEntry = findEntryForDate(recentEntries, todayIso);
        dashboardSummary = fixture.dashboard;
        userPreferences = fixture.preferences;
        return;
      }

      const start = shiftIsoDate(todayIso, -6);
      const [entriesResult, summaryResult, preferencesResult] = await Promise.allSettled([
        listEntries({ start_date: start, end_date: todayIso }),
        fetchDashboardSummary(todayIso),
        fetchUserPreferences(),
      ]);

      if (entriesResult.status === 'rejected') throw entriesResult.reason;

      recentEntries = entriesResult.value;
      todayEntry = findEntryForDate(recentEntries, todayIso);
      if (!todayEntry && canUseOfflineSync()) {
        const localToday = await findLocalEntryByDateSlot(todayIso, 'day');
        if (localToday) {
          todayEntry = localEntryToEntryResponse(localToday, get(currentUser)?.id ?? '');
        }
      }
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
    $auth.status === 'authenticated' &&
    $devForceVisualizations &&
    dashboardLoaded &&
    !dashboardLoading &&
    activeDevFixtureKey !== devFixtureKey()
  ) {
    void loadDashboard();
    void loadInsights();
  }

  $: if (
    dashboardLoaded &&
    $auth.status === 'authenticated' &&
    dashboardSummary?.entry_count === 0 &&
    userPreferences &&
    !userPreferences.onboarding_retro_completed &&
    !firstEntrySheetOpened &&
    !entrySheetOpen &&
    !isOpenEntryRequested($page.url.searchParams)
  ) {
    firstEntrySheetOpened = true;
    openEntry(todayIso);
  }

  async function dismissFirstWeekBanner(): Promise<void> {
    const dismissed = new Set(userPreferences?.dismissed_insight_keys ?? []);
    dismissed.add(EARLY_CONTEXT_PATTERN_KEY);
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
    if (get(auth).status === 'authenticated' && !dashboardLoaded) {
      void loadDashboard();
      void loadInsights();
    }
    return entrySheetSaveSignal.subscribe((count) => {
      if (count === 0) return;
      void loadDashboard();
      void loadInsights();
    });
  });
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

{#if $auth.status === 'authenticated'}
  <div class="home-screen screen-stack screen-stack--loose">
    <ScreenHeader title={$_('nav.home')} visuallyHidden />
    {#if showPwaInstallBanner}
      <section class="home-install" data-testid="pwa-install-banner">
        <div>
          <h2>{$_('pwa.install.title')}</h2>
          <p>{$_('pwa.install.body')}</p>
        </div>
        <div class="home-install__actions">
          <Button variant="ghost" size="sm" on:click={() => pwaInstallStore.dismiss()}>
            {$_('pwa.install.dismiss')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            on:click={() => void pwaInstallStore.promptInstall()}
          >
            {$_('pwa.install.cta')}
          </Button>
        </div>
      </section>
    {/if}

    <!-- Zone 1: date + work context + compact entry action -->
    <section class="home-zone home-zone--context" data-testid="home-zone-context">
      <HomeTodayContext
        {todayIso}
        {todayEntry}
        loading={dashboardLoading && !dashboardLoaded}
        on:logToday={() => openEntry(todayIso)}
      />
    </section>

    <!-- Zone 2: daily brief (best-effort) -->
    <section class="home-zone" data-testid="home-zone-insight">
      {#if showFirstWeekBanner}
        <FirstWeekInsightBanner insight={contextInsight} on:dismiss={dismissFirstWeekBanner} />
      {/if}
      <HomeDailyBrief
        entries={recentEntries}
        {latestInsight}
        maturity={insightMaturity}
        loading={insightLoading && !latestInsight}
        workContextSummary={dashboardSummary?.work_context_summary ?? []}
      />
      <HomeWeekdayOverview
        insights={$rankedInsights}
        {weekdayInsight}
        weekdaySummary={dashboardSummary?.weekday_summary ?? []}
        loading={(insightLoading || (dashboardLoading && !dashboardLoaded)) &&
          !(dashboardSummary?.weekday_summary?.length ?? 0) &&
          !weekdayInsight}
      />
    </section>

    <!-- Zone 3: primary CTA when today is not logged -->
    {#if !todayEntry}
      <section class="home-zone home-zone--foot" data-testid="home-zone-cta">
        <Button
          type="button"
          variant="primary"
          size="lg"
          fullWidth
          stacked
          className="home-cta"
          data-testid="home-cta"
          on:click={() => openEntry(todayIso)}
        >
          <span class="text-lg font-semibold">{$_('home.cta_log_today')}</span>
          <span class="text-sm home-cta__hint">{$_('entry.subtitle')}</span>
        </Button>
      </section>
    {/if}
  </div>
{:else}
  <LandingPage />
{/if}

<style>
  .home-screen {
    display: flex;
    flex-direction: column;
  }

  .home-zone {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .home-zone--context {
    order: 1;
  }

  :global([data-testid='home-zone-insight']) {
    order: 2;
  }

  .home-zone--foot {
    order: 3;
    gap: var(--screen-gap);
  }

  .home-install {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid color-mix(in srgb, var(--color-primary) 28%, var(--color-border));
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
  }

  .home-install h2,
  .home-install p {
    margin: 0;
  }

  .home-install h2 {
    font-size: var(--text-base);
  }

  .home-install p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .home-install__actions {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  :global(.home-cta) {
    border: 1px solid color-mix(in oklch, var(--color-primary) 25%, transparent);
  }

  :global(.home-cta .home-cta__hint) {
    color: color-mix(in srgb, var(--color-text-inverse) 78%, transparent);
  }
</style>
