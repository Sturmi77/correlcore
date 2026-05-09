<script lang="ts">
  /**
   * Home route — Issue #97 + ADR-0014 (M1.5 Home-Dashboard).
   *
   * Two faces, gated by auth state:
   *   - Anonymous → existing landing (logo + tagline + theme toggle).
   *   - Authenticated → today-view + recent-entries list, 7-day summary
   *     and 14-day mood sparkline.
   *
   * Loader strategy (ADR-0014):
   *   - Fetch the last 14 days for sparkline + recent-entries list.
   *   - Compute the entry-streak from those 14 days; if it equals 14
   *     (rare) we run a second query covering 30 days so the streak can
   *     keep growing. Numbers ≥ 30 render as "30+".
   *   - Tag/symptom decorations on individual cards are loaded lazily
   *     inside `HomeRecentEntries` (Promise.allSettled per entry).
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, currentUser, logout } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchEntryStreak, type EntryStreakResponse } from '$lib/api/stats';
  import { findEntryForDate, greetingKey, localIsoDate } from '$lib/utils/home';
  import { computeEntryStreak, shiftIsoDate } from '$lib/utils/streak';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import HomeRecentEntries from '$lib/components/home/HomeRecentEntries.svelte';
  import HomeSummary from '$lib/components/home/HomeSummary.svelte';
  import HomeSparkline from '$lib/components/home/HomeSparkline.svelte';

  // ---------------------------------------------------------------------
  // Constants & derived state.
  // ---------------------------------------------------------------------

  /** ADR-0014: 14-day baseline window covers sparkline + recent-list. */
  const BASELINE_DAYS = 14;
  /** Extension cap when the streak fills the baseline window. */
  const EXTENDED_DAYS = 30;

  const todayIso = localIsoDate(new Date());
  const greetingI18nKey = greetingKey(new Date().getHours());

  let todayEntry: EntryResponse | null = null;
  let recentEntries: EntryResponse[] = [];
  let streakEntries: EntryResponse[] = [];
  let backendStreak: EntryStreakResponse | null = null;
  let dashboardLoading = false;
  let dashboardLoaded = false;
  /** True once the loader had to query the extended 30-day window. */
  let streakCapped = false;

  /**
   * Slice the 14-day window for the 7-day summary so HomeSummary's
   * averages and counts only consider the last 7 days (ADR-0014).
   */
  $: summaryWindowStart = shiftIsoDate(todayIso, -6);
  $: summaryEntries = recentEntries.filter(
    (e) => e.entry_date >= summaryWindowStart && e.entry_date <= todayIso,
  );

  async function loadDashboard(): Promise<void> {
    dashboardLoading = true;
    try {
      const start = shiftIsoDate(todayIso, -(BASELINE_DAYS - 1));
      const baseline = await listEntries({
        start_date: start,
        end_date: todayIso,
      });
      backendStreak = await fetchEntryStreak(todayIso);
      recentEntries = baseline;
      todayEntry = findEntryForDate(baseline, todayIso);

      // Streak math: if the entry-streak fills the baseline window we
      // expand the lookup so 7+ day streaks can render correctly. We
      // cap at 30 ("30+") to keep the request cheap.
      const baselineStreak = computeEntryStreak(baseline, todayIso);
      if (baselineStreak >= BASELINE_DAYS) {
        const extendedStart = shiftIsoDate(todayIso, -(EXTENDED_DAYS - 1));
        try {
          streakEntries = await listEntries({
            start_date: extendedStart,
            end_date: todayIso,
          });
          streakCapped = true;
        } catch {
          streakEntries = baseline;
          streakCapped = false;
        }
      } else {
        streakEntries = baseline;
        streakCapped = false;
      }
    } catch {
      recentEntries = [];
      streakEntries = [];
      todayEntry = null;
      backendStreak = null;
      streakCapped = false;
    } finally {
      dashboardLoading = false;
      dashboardLoaded = true;
    }
  }

  $: if ($auth.status === 'authenticated' && !dashboardLoaded && !dashboardLoading) {
    void loadDashboard();
  }

  async function handleLogout(): Promise<void> {
    await logout();
    todayEntry = null;
    recentEntries = [];
    streakEntries = [];
    dashboardLoaded = false;
    streakCapped = false;
    backendStreak = null;
    void goto('/', { replaceState: true });
  }

  $: displayName = $currentUser?.display_name?.trim() || $currentUser?.email || '';

  onMount(() => {
    if ($auth.status === 'authenticated' && !dashboardLoaded) {
      void loadDashboard();
    }
  });
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

{#if $auth.status === 'authenticated'}
  <!-- ================================================================
       Authenticated Home - "Heute-Ansicht" + Dashboard (ADR-0014)
       Kein eigener <main> — page-shell in +layout.svelte übernimmt
       Padding (Safe-Area), max-width und Zentrierung.
       ================================================================ -->
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

    <!-- Hero CTA -->
    <section>
      {#if todayEntry}
        <a
          class="card p-6 flex flex-col items-center gap-2 text-center hover:variant-soft-primary"
          href="/entries/new"
          data-testid="home-cta"
        >
          <span class="text-lg font-semibold">{$_('home.cta_edit_entry')}</span>
          <span class="text-sm" style="color: var(--color-text-muted)">{todayIso}</span>
        </a>
      {:else}
        <a
          class="card p-6 flex flex-col items-center gap-2 text-center hover:variant-soft-primary"
          href="/entries/new"
          data-testid="home-cta"
        >
          <span class="text-lg font-semibold">{$_('home.cta_new_entry')}</span>
          <span class="text-sm" style="color: var(--color-text-muted)"
            >{$_('entry.subtitle')}</span
          >
        </a>
      {/if}
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
        {streakEntries}
        {todayIso}
        {streakCapped}
        backendStreak={backendStreak?.current_streak ?? null}
        loading={dashboardLoading && !dashboardLoaded}
      />
    </section>

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
  </div>
{:else}
  <!-- ================================================================
       Anonymous Landing
       ================================================================ -->
  <div class="flex flex-col items-center justify-center gap-8 min-h-[80dvh]">
    <!-- Logo -->
    <div class="flex flex-col items-center gap-4">
      <svg
        aria-label="MoodSync"
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

    <!-- Theme toggle -->
    <div class="flex items-center gap-3">
      <span style="font-size: var(--text-sm); color: var(--color-text-faint)">Theme:</span>
      <ThemeToggle testId="landing-theme-toggle" />
    </div>

    <!-- Status badge -->
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
