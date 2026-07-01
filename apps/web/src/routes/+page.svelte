<script lang="ts">
  /**
   * Home route — ADR-0017 Screen 1 (M3.5 Sprint 4).
   *
   * Authenticated home uses exactly three information zones:
   *   1. Today context (date, work context, compact log/edit action)
   *   2. Daily Brief: latest insight summary OR phase fallback (brief-first)
   *   3. 7-day mood sparkline + secondary entry CTA
   *
   * Insight load never blocks the CTA. No matrix, summary grid, or
   * recent-entries list on Home — those live under Trends / Insights.
   */

  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, currentUser } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchDashboardSummary, type DashboardSummaryResponse } from '$lib/api/dashboard';
  import {
    fetchSymptomHeatmap,
    fetchTagHeatmap,
    type SymptomHeatmapResponse,
    type TagHeatmapResponse,
  } from '$lib/api/stats';
  import { insightStore, rankedInsights, loadInsights } from '$lib/stores/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { mockDashboardSummary, mockEntries, mockUserPreferences } from '$lib/dev/mockEntries';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { pwaInstallStore } from '$lib/stores/pwaInstall';
  import { findEntryForDate, localIsoDate } from '$lib/utils/home';
  import { shiftIsoDate } from '$lib/utils/streak';
  import Button from '$lib/components/common/Button.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import FirstWeekInsightBanner from '$lib/components/home/FirstWeekInsightBanner.svelte';
  import HomeSparkline from '$lib/components/home/HomeSparkline.svelte';
  import HomeTodayContext from '$lib/components/home/HomeTodayContext.svelte';
  import HomeDailyBrief from '$lib/components/home/HomeDailyBrief.svelte';
  import EntrySheet from '$lib/components/entries/EntrySheet.svelte';
  import {
    entryDateFromSearchParams,
    entryWorkspacePath,
    isOpenEntryRequested,
  } from '$lib/navigation/openEntry';
  import { prefersEntrySheet } from '$lib/navigation/entryNavigation';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';

  const HOME_SPARKLINE_DAYS = 7;
  const HOME_SPARKLINE_MIN_ENTRIES = 3;
  const FIRST_WEEK_PATTERN_KEY = 'first_week_pattern';

  const todayIso = localIsoDate(new Date());

  let todayEntry: EntryResponse | null = null;
  let recentEntries: EntryResponse[] = [];
  let dashboardSummary: DashboardSummaryResponse | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let tagHeatmap: TagHeatmapResponse | null = null;
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let dashboardLoading = false;
  let dashboardLoaded = false;
  let entrySheetOpen = false;
  let entrySheetDate = todayIso;
  let openEntryHandled = false;
  let firstEntrySheetOpened = false;
  let preferEntrySheet = true;
  let entryViewportMedia: MediaQueryList | null = null;

  $: latestInsight = $insightStore.latest;
  $: insightMaturity = $insightStore.insightMaturity;
  $: insightLoading = $insightStore.loading;
  $: weekdayInsight = $rankedInsights.find((i) => i.insight_type === 'weekday_pattern') ?? null;
  $: firstWeekDismissed =
    userPreferences?.dismissed_insight_keys.includes(FIRST_WEEK_PATTERN_KEY) ?? false;
  $: showFirstWeekBanner = Boolean(weekdayInsight && !firstWeekDismissed);
  $: dayEntriesForSparkline = recentEntries.filter((entry) => entry.slot === 'day');
  $: showHomeSparkline = dayEntriesForSparkline.length >= HOME_SPARKLINE_MIN_ENTRIES;
  $: showOnboardingTags = Boolean(
    userPreferences &&
      !userPreferences.onboarding_retro_completed &&
      dashboardSummary?.entry_count === 0
  );
  $: showPwaInstallBanner = Boolean(
    $pwaInstallStore.promptEvent &&
      !$pwaInstallStore.dismissed &&
      !$pwaInstallStore.installed &&
      ((dashboardSummary?.entry_count ?? 0) >= 1 || userPreferences?.onboarding_retro_completed)
  );

  function syncEntrySurface(): void {
    preferEntrySheet = prefersEntrySheet();
  }

  function openEntry(date: string = todayIso): void {
    if (preferEntrySheet) {
      entrySheetDate = date;
      entrySheetOpen = true;
      return;
    }
    void goto(entryWorkspacePath(date));
  }

  function openEntrySheet(date: string = todayIso) {
    openEntry(date);
  }

  function onEntrySheetSaved() {
    void loadDashboard();
    void loadInsights();
  }

  function stripOpenEntryQuery(): void {
    const url = new URL($page.url);
    if (!isOpenEntryRequested(url.searchParams)) return;
    url.searchParams.delete('openEntry');
    url.searchParams.delete('date');
    const next = `${url.pathname}${url.search}${url.hash}`;
    void goto(next || '/', { replaceState: true, keepFocus: true, noScroll: true });
  }

  function maybeOpenEntryFromQuery(): void {
    if (openEntryHandled || !dashboardLoaded || get(auth).status !== 'authenticated') return;
    if (!isOpenEntryRequested($page.url.searchParams)) return;
    openEntryHandled = true;
    const date = entryDateFromSearchParams($page.url.searchParams) ?? todayIso;
    openEntry(date);
    stripOpenEntryQuery();
  }

  async function loadDashboard(): Promise<void> {
    dashboardLoading = true;
    try {
      if (get(devForceVisualizations)) {
        recentEntries = mockEntries.slice(0, HOME_SPARKLINE_DAYS);
        todayEntry = findEntryForDate(recentEntries, todayIso);
        dashboardSummary = { ...mockDashboardSummary, entry_count: $devPhase.entryCount };
        tagHeatmap = null;
        symptomHeatmap = null;
        userPreferences = {
          ...mockUserPreferences,
          onboarding_retro_completed: $devPhase.onboardingCompleted,
          onboarding_profile_completed: $devPhase.onboardingCompleted,
        };
        return;
      }

      const start = shiftIsoDate(todayIso, -(HOME_SPARKLINE_DAYS - 1));
      const [entriesResult, summaryResult, preferencesResult, tagsResult, symptomsResult] =
        await Promise.allSettled([
          listEntries({ start_date: start, end_date: todayIso }),
          fetchDashboardSummary(todayIso),
          fetchUserPreferences(),
          fetchTagHeatmap({ start_date: start, end_date: todayIso }),
          fetchSymptomHeatmap({ start_date: start, end_date: todayIso }),
        ]);

      if (entriesResult.status === 'rejected') throw entriesResult.reason;

      recentEntries = entriesResult.value;
      todayEntry = findEntryForDate(recentEntries, todayIso);
      dashboardSummary = summaryResult.status === 'fulfilled' ? summaryResult.value : null;
      userPreferences = preferencesResult.status === 'fulfilled' ? preferencesResult.value : null;
      tagHeatmap = tagsResult.status === 'fulfilled' ? tagsResult.value : null;
      symptomHeatmap = symptomsResult.status === 'fulfilled' ? symptomsResult.value : null;
    } catch {
      recentEntries = [];
      todayEntry = null;
      dashboardSummary = null;
      userPreferences = null;
      tagHeatmap = null;
      symptomHeatmap = null;
    } finally {
      dashboardLoading = false;
      dashboardLoaded = true;
    }
  }

  $: if ($auth.status === 'authenticated' && !dashboardLoaded && !dashboardLoading) {
    void loadDashboard();
    void loadInsights();
  }

  $: if (dashboardLoaded && $auth.status === 'authenticated') {
    maybeOpenEntryFromQuery();
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
    if (get(auth).status === 'authenticated' && !dashboardLoaded) {
      void loadDashboard();
      void loadInsights();
    }
    if (typeof window !== 'undefined') {
      entryViewportMedia =
        window.matchMedia(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`) ?? null;
      syncEntrySurface();
      entryViewportMedia?.addEventListener('change', syncEntrySurface);
    }
  });

  onDestroy(() => {
    entryViewportMedia?.removeEventListener('change', syncEntrySurface);
  });
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

{#if $auth.status === 'authenticated'}
  <div class="home-screen">
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
        on:logToday={() => openEntrySheet(todayIso)}
      />
    </section>

    <!-- Zone 2: daily brief (best-effort) -->
    <section class="home-zone" data-testid="home-zone-insight">
      {#if showFirstWeekBanner}
        <FirstWeekInsightBanner on:dismiss={dismissFirstWeekBanner} />
      {:else}
        <HomeDailyBrief
          entries={recentEntries}
          {latestInsight}
          maturity={insightMaturity}
          loading={insightLoading && !latestInsight}
          {tagHeatmap}
          {symptomHeatmap}
        />
      {/if}
    </section>

    <!-- Zone 3: sparkline + primary CTA -->
    <section class="home-zone home-zone--foot" data-testid="home-zone-sparkline-cta">
      {#if showHomeSparkline}
        <HomeSparkline
          entries={recentEntries}
          {todayIso}
          days={HOME_SPARKLINE_DAYS}
          loading={dashboardLoading && !dashboardLoaded}
        />
      {/if}

      <Button
        type="button"
        variant={todayEntry ? 'ghost' : 'primary'}
        size={todayEntry ? 'md' : 'lg'}
        fullWidth
        stacked={!todayEntry}
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

    {#if preferEntrySheet}
    <EntrySheet
      bind:open={entrySheetOpen}
      initialDate={entrySheetDate}
      onboardingTagsEnabled={showOnboardingTags}
      on:saved={onEntrySheetSaved}
    />
  {/if}
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

  .home-zone--context {
    order: 1;
  }

  :global([data-testid='home-zone-insight']) {
    order: 2;
  }

  .home-zone--foot {
    order: 3;
    gap: var(--space-5);
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
