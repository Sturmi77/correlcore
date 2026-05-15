<script lang="ts">
  /**
   * Home route — Issue #97 + ADR-0014 (M1.5 Home-Dashboard).
   * M3.1 #161: renamed streak props to consistency (ADR-0017 no-gamification).
   * M3.1 #167: HomeInsight replaced by InsightCard + insightStore (TODO-1,3,4).
   *
   * Two faces, gated by auth state:
   *   - Anonymous → existing landing (logo + tagline + theme toggle).
   *   - Authenticated → today-view + recent-entries list, 7-day summary
   *     and 14-day mood sparkline.
   *
   * Loader strategy (ADR-0014):
   *   - Fetch the last 14 days for sparkline + recent-entries list.
   *   - Compute the entry-consistency from those 14 days; if it equals 14
   *     (rare) we run a second query covering 30 days so the number can
   *     keep growing. Numbers ≥ 30 render as "30+".
   *   - Tag/symptom decorations on individual cards are loaded lazily
   *     inside `HomeRecentEntries` (Promise.allSettled per entry).
   *   - Insights are owned by insightStore (ADR-0017) — isolated from
   *     dashboard loading state so a fetch failure never blocks the CTA.
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, currentUser, logout } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchDashboardSummary, type DashboardSummaryResponse } from '$lib/api/dashboard';
  import {
    insightStore,
    rankedInsights,
    loadInsights,
    dismissInsight,
    resetInsightStore,
  } from '$lib/stores/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { fetchEntryStreak, type EntryStreakResponse } from '$lib/api/stats';
  import { findEntryForDate, greetingKey, localIsoDate } from '$lib/utils/home';
  import { computeEntryStreak, shiftIsoDate } from '$lib/utils/streak';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import FirstWeekInsightBanner from '$lib/components/home/FirstWeekInsightBanner.svelte';
  import HomeRecentEntries from '$lib/components/home/HomeRecentEntries.svelte';
  import HomeSummary from '$lib/components/home/HomeSummary.svelte';
  import HomeSparkline from '$lib/components/home/HomeSparkline.svelte';
  import InsightConfidenceScale from '$lib/components/home/InsightConfidenceScale.svelte';
  import WeekdayPatternChart from '$lib/components/home/WeekdayPatternChart.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import EntrySheet from '$lib/components/entries/EntrySheet.svelte';

  // ---------------------------------------------------------------------
  // Constants & derived state.
  // ---------------------------------------------------------------------

  /** ADR-0014: 14-day baseline window covers sparkline + recent-list. */
  const BASELINE_DAYS = 14;
  /** Extension cap when the consistency fills the baseline window. */
  const EXTENDED_DAYS = 30;
  const FIRST_WEEK_PATTERN_KEY = 'first_week_pattern';

  const todayIso = localIsoDate(new Date());
  const greetingI18nKey = greetingKey(new Date().getHours());

  let todayEntry: EntryResponse | null = null;
  let recentEntries: EntryResponse[] = [];
  let consistencyEntries: EntryResponse[] = [];
  let backendStreakData: EntryStreakResponse | null = null;
  let dashboardSummary: DashboardSummaryResponse | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let dashboardLoading = false;
  let dashboardLoaded = false;
  /** True once the loader had to query the extended 30-day window. */
  let consistencyCapped = false;
  let entrySheetOpen = false;
  let entrySheetDate = todayIso;

  // Insight state comes exclusively from insightStore (ADR-0017).
  $: latestInsight = $insightStore.latest;
  $: insightLoading = $insightStore.loading;
  $: insightError = $insightStore.error ?? '';
  $: weekdayInsight = $rankedInsights.find((i) => i.insight_type === 'weekday_pattern') ?? null;
  // Correlation matrix: all pointbiserial insights with enough confidence.
  $: matrixInsights = $rankedInsights.filter(
    (i) => i.insight_type === 'pointbiserial' && (i.confidence ?? 0) >= 0.2
  );

  /**
   * Slice the 14-day window for the 7-day summary so HomeSummary's
   * averages and counts only consider the last 7 days (ADR-0014).
   */
  $: summaryWindowStart = shiftIsoDate(todayIso, -6);
  $: summaryEntries = recentEntries.filter(
    (e) => e.entry_date >= summaryWindowStart && e.entry_date <= todayIso
  );

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
      const start = shiftIsoDate(todayIso, -(BASELINE_DAYS - 1));
      const [baselineResult, streakResult, summaryResult, preferencesResult] =
        await Promise.allSettled([
          listEntries({
            start_date: start,
            end_date: todayIso,
          }),
          fetchEntryStreak(todayIso),
          fetchDashboardSummary(todayIso),
          fetchUserPreferences(),
        ]);

      if (baselineResult.status === 'rejected') throw baselineResult.reason;

      const baseline = baselineResult.value;
      backendStreakData = streakResult.status === 'fulfilled' ? streakResult.value : null;
      dashboardSummary = summaryResult.status === 'fulfilled' ? summaryResult.value : null;
      userPreferences = preferencesResult.status === 'fulfilled' ? preferencesResult.value : null;
      recentEntries = baseline;
      todayEntry = findEntryForDate(baseline, todayIso);

      // Consistency math: if the entry-run fills the baseline window we
      // expand the lookup so 7+ day runs can render correctly. We
      // cap at 30 ("30+") to keep the request cheap.
      const baselineConsistency = computeEntryStreak(baseline, todayIso);
      if (baselineConsistency >= BASELINE_DAYS) {
        const extendedStart = shiftIsoDate(todayIso, -(EXTENDED_DAYS - 1));
        try {
          consistencyEntries = await listEntries({
            start_date: extendedStart,
            end_date: todayIso,
          });
          consistencyCapped = true;
        } catch {
          consistencyEntries = baseline;
          consistencyCapped = false;
        }
      } else {
        consistencyEntries = baseline;
        consistencyCapped = false;
      }
    } catch {
      recentEntries = [];
      consistencyEntries = [];
      todayEntry = null;
      backendStreakData = null;
      dashboardSummary = null;
      userPreferences = null;
      consistencyCapped = false;
    } finally {
      dashboardLoading = false;
      dashboardLoaded = true;
    }
  }

  $: if ($auth.status === 'authenticated' && !dashboardLoaded && !dashboardLoading) {
    void loadDashboard();
    void loadInsights();
  }

  async function handleLogout(): Promise<void> {
    await logout();
    todayEntry = null;
    recentEntries = [];
    consistencyEntries = [];
    dashboardLoaded = false;
    consistencyCapped = false;
    backendStreakData = null;
    dashboardSummary = null;
    userPreferences = null;
    resetInsightStore();
    void goto('/', { replaceState: true });
  }

  $: displayName = $currentUser?.display_name?.trim() || $currentUser?.email || '';
  $: firstWeekDismissed =
    userPreferences?.dismissed_insight_keys.includes(FIRST_WEEK_PATTERN_KEY) ?? false;
  $: showFirstWeekBanner = Boolean(weekdayInsight && !firstWeekDismissed);
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
      // Keep the optimistic dismissal for this session.
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
  <div class="flex flex-col gap-6 pt-4 pb-8">
    <!-- Top bar: theme toggle + logout -->
    <header class="flex items-center justify-between">
      <ThemeToggle testId="home-theme-toggle" />
      <button
        class="btn btn-sm variant-ghost-surface"
        type="button"
        on:click={handleLogout}
        data-testid="home-logout"
      >
        {$_('auth.logout.label')}
      </button>
    </header>

    <!-- Greeting -->
    <section class="flex flex-col items-center gap-2 text-center" data-testid="home-greeting">
      <h1 class="h1" style="font-size: var(--text-xl)">
        {$_(greetingI18nKey)}{displayName ? `, ${displayName}` : ''}
      </h1>
    </section>

    <!-- Today status -->
    <section class="flex flex-col items-center gap-3">
      {#if dashboardLoading && !dashboardLoaded}
        <span class="badge variant-soft text-xs" aria-live="polite">
          {$_('home.loading_today')}
        </span>
      {:else if todayEntry}
        <span
          class="badge variant-soft-success text-xs"
          data-testid="home-today-status"
          aria-live="polite"
        >
          {$_('home.entry_today_present')} ✓
        </span>
      {:else}
        <span
          class="badge variant-soft-warning text-xs"
          data-testid="home-today-status"
          aria-live="polite"
        >
          {$_('home.no_entry_today')}
        </span>
      {/if}
    </section>

    <!-- Hero CTA — opens entry bottom sheet (ADR-0017 Screen 2) -->
    <section>
      <button
        type="button"
        class="card p-6 flex flex-col items-center gap-2 text-center hover:variant-soft-primary w-full"
        data-testid="home-cta"
        on:click={() => openEntrySheet(todayIso)}
      >
        {#if todayEntry}
          <span class="text-lg font-semibold">{$_('home.cta_edit_entry')}</span>
          <span class="text-sm" style="color: var(--color-text-muted)">{todayIso}</span>
        {:else}
          <span class="text-lg font-semibold">{$_('home.cta_new_entry')}</span>
          <span class="text-sm" style="color: var(--color-text-muted)">{$_('entry.subtitle')}</span>
        {/if}
      </button>
    </section>

    <!-- Recent-entries list -->
    <section>
      <HomeRecentEntries
        {todayIso}
        entries={recentEntries}
        loading={dashboardLoading && !dashboardLoaded}
      />
    </section>

    <!-- 7-day summary -->
    <section>
      <HomeSummary
        entries={summaryEntries}
        {consistencyEntries}
        {todayIso}
        {consistencyCapped}
        backendConsistency={backendStreakData?.current_streak ?? null}
        loading={dashboardLoading && !dashboardLoaded}
      />
    </section>

    {#if showFirstWeekBanner}
      <section>
        <FirstWeekInsightBanner on:dismiss={dismissFirstWeekBanner} />
      </section>
    {/if}

    <!-- Permanent insight confidence scale -->
    <section>
      <InsightConfidenceScale
        confidenceScore={dashboardSummary?.confidence_score ?? 0.05}
        currentTier={dashboardSummary?.insight_tier ?? 'none'}
        entryCount={dashboardSummary?.entry_count ?? 0}
        loading={dashboardLoading && !dashboardLoaded}
      />
    </section>

    {#if weekdayInsight}
      <section>
        <WeekdayPatternChart insight={weekdayInsight} />
      </section>
    {/if}

    <!-- Latest insight card (ADR-0017: InsightCard replaces HomeInsight) -->
    <section>
      <InsightCard
        insight={latestInsight}
        loading={insightLoading && !latestInsight}
        error={insightError}
        on:dismiss={(e) => void dismissInsight(e.detail.id)}
        on:retry={() => void loadInsights()}
      />
    </section>

    <!-- Correlation matrix (pointbiserial insights, confidence >= 0.2) -->
    {#if !insightLoading && matrixInsights.length >= 2}
      <section>
        <InsightMatrix insights={matrixInsights} />
      </section>
    {/if}

    <!-- 14-day mood sparkline -->
    <section>
      <HomeSparkline
        entries={recentEntries}
        {todayIso}
        loading={dashboardLoading && !dashboardLoaded}
      />
    </section>

    <nav class="flex gap-3 justify-center text-sm">
      <a class="btn btn-sm variant-soft-primary" href="/trends">{$_('trends.title')}</a>
      <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('nav.settings')}</a>
    </nav>

    <EntrySheet
      bind:open={entrySheetOpen}
      initialDate={entrySheetDate}
      on:saved={onEntrySheetSaved}
    />
  </div>
{:else}
  <div class="flex flex-col items-center justify-center gap-8 min-h-[80dvh]">
    <!-- Logo -->
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
      <span style="font-size: var(--text-sm); color: var(--color-text-faint)">Theme:</span>
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
