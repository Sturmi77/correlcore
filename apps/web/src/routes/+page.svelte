<script lang="ts">
  /**
   * Home route — Issue #97.
   *
   * Two faces, gated by auth state:
   *   - Anonymous → existing landing (logo + tagline + theme toggle).
   *   - Authenticated → today-view: time-aware greeting, today-status badge,
   *     hero CTA to /entries/new (or "edit today's entry" if one exists),
   *     logout button. Theme toggle stays.
   *
   * Deliberately minimal for M1. No streak counter, no recent-entries list,
   * no charts — those land with M2 (visualisation milestone). See
   * DESIGN_DOCUMENT.md "Home-Screen-Heuristik".
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { theme } from '$lib/stores/theme';
  import { auth, currentUser, logout } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { findEntryForDate, greetingKey, localIsoDate } from '$lib/utils/home';

  $: currentTheme = $theme;

  // ---------------------------------------------------------------------
  // Today-view state (only relevant for authenticated users).
  // ---------------------------------------------------------------------

  const todayIso = localIsoDate(new Date());
  const greetingI18nKey = greetingKey(new Date().getHours());

  let todayEntry: EntryResponse | null = null;
  let todayLoading = false;
  let todayLoaded = false;

  async function loadTodayEntry(): Promise<void> {
    todayLoading = true;
    try {
      const entries = await listEntries({
        start_date: todayIso,
        end_date: todayIso,
        limit: 1,
      });
      todayEntry = findEntryForDate(entries, todayIso);
    } catch {
      // Best-effort. The "no entry today yet" copy is a safe default and
      // the user can still hit the CTA.
      todayEntry = null;
    } finally {
      todayLoading = false;
      todayLoaded = true;
    }
  }

  // Trigger today-load whenever auth flips to authenticated.
  $: if ($auth.status === 'authenticated' && !todayLoaded && !todayLoading) {
    void loadTodayEntry();
  }

  async function handleLogout(): Promise<void> {
    await logout();
    todayEntry = null;
    todayLoaded = false;
    void goto('/', { replaceState: true });
  }

  // Greeting line: "<greeting>, <display_name|email>"
  $: displayName = $currentUser?.display_name?.trim() || $currentUser?.email || '';

  onMount(() => {
    if ($auth.status === 'authenticated' && !todayLoaded) {
      void loadTodayEntry();
    }
  });
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

{#if $auth.status === 'authenticated'}
  <!-- ============================================================
       Authenticated Home — "Heute-Ansicht"
       ============================================================ -->
  <main class="flex-1 flex flex-col items-center p-6 gap-8 w-full">
    <!-- Top bar: theme toggle + logout -->
    <header class="w-full max-w-xl flex items-center justify-between">
      <button
        class="btn btn-sm variant-ghost-surface"
        on:click={() => theme.toggle()}
        aria-label={currentTheme === 'dark' ? $_('theme.toggle_light') : $_('theme.toggle_dark')}
      >
        {#if currentTheme === 'dark'}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="5" />
            <path
              d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
            />
          </svg>
          <span>Hell</span>
        {:else}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
          <span>Dunkel</span>
        {/if}
      </button>

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
    <section class="w-full max-w-xl flex flex-col items-center gap-3">
      {#if todayLoading}
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
    <section class="w-full max-w-xl">
      {#if todayEntry}
        <a
          class="card p-6 flex flex-col items-center gap-2 text-center hover:variant-soft-primary"
          href="/entries/new"
          data-testid="home-cta"
        >
          <span class="text-lg font-semibold">{$_('home.cta_edit_entry')}</span>
          <span class="text-sm opacity-70">{todayIso}</span>
        </a>
      {:else}
        <a
          class="card p-6 flex flex-col items-center gap-2 text-center hover:variant-soft-primary"
          href="/entries/new"
          data-testid="home-cta"
        >
          <span class="text-lg font-semibold">{$_('home.cta_new_entry')}</span>
          <span class="text-sm opacity-70">{$_('entry.subtitle')}</span>
        </a>
      {/if}
    </section>
  </main>
{:else}
  <!-- ============================================================
       Anonymous Landing (unchanged)
       ============================================================ -->
  <main class="flex-1 flex flex-col items-center justify-center p-6 gap-8">
    <!-- Logo -->
    <div class="flex flex-col items-center gap-4">
      <svg
        aria-label="MoodSync"
        viewBox="0 0 48 48"
        width="64"
        height="64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        class="text-current"
      >
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="3" opacity="0.25" />
        <path
          d="M24 4 A20 20 0 0 1 44 24"
          stroke="#01696f"
          stroke-width="3"
          stroke-linecap="round"
        />
        <path
          d="M16 26 Q24 34 32 26"
          stroke="#01696f"
          stroke-width="2.5"
          stroke-linecap="round"
          fill="none"
        />
        <circle cx="19" cy="20" r="1.5" fill="#01696f" />
        <circle cx="29" cy="20" r="1.5" fill="#01696f" />
      </svg>

      <h1 class="h1 text-center" style="font-size: var(--text-xl)">
        {$_('app.name')}
      </h1>
      <p class="text-surface-600-300-token text-center" style="font-size: var(--text-base)">
        {$_('app.tagline')}
      </p>
    </div>

    <!-- Theme toggle -->
    <div class="flex items-center gap-3">
      <span class="text-sm opacity-60">Theme:</span>
      <button
        class="btn btn-sm variant-ghost-surface"
        on:click={() => theme.toggle()}
        aria-label={currentTheme === 'dark' ? $_('theme.toggle_light') : $_('theme.toggle_dark')}
      >
        {#if currentTheme === 'dark'}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="5" />
            <path
              d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
            />
          </svg>
          <span>Hell</span>
        {:else}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
          <span>Dunkel</span>
        {/if}
      </button>
    </div>

    <!-- Status badge -->
    <div class="badge variant-soft-warning text-xs">Pre-Alpha — M0 Setup</div>
  </main>
{/if}
