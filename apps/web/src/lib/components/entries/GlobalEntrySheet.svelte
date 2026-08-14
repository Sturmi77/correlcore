<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import {
    closeEntrySheet,
    entrySheetStore,
    notifyEntrySheetSaved,
    openEntrySheet,
  } from '$lib/stores/entrySheet';
  import { fetchDashboardSummary } from '$lib/api/dashboard';
  import { fetchUserPreferences } from '$lib/api/preferences';
  import { fetchUserProfile, type WorkContextTypical } from '$lib/api/profile';
  import { entryDateFromSearchParams, isOpenEntryRequested } from '$lib/navigation/openEntry';
  import { isoDate } from '$lib/utils/entryForm';
  import { shouldShowOnboardingTags, shouldRedirectToOnboarding } from '$lib/utils/onboardingEntry';
  import { hasOnboardingSuggestionStash } from '$lib/utils/onboardingSuggestionStash';
  import EntrySheet from './EntrySheet.svelte';

  let sheetOpen = false;
  let workContextTypical: WorkContextTypical | null = null;
  let cycleTrackingEnabled = true;
  /** User id whose profile defaults are currently cached (null = none). */
  let profileLoadedForUserId: string | null = null;
  let openFromQueryPending = false;

  $: sheetOpen = $entrySheetStore.open;

  // Re-read the cycle preference each time the sheet opens so a Settings toggle
  // made earlier in the same session is reflected without a reload (the initial
  // load is guarded by `profileLoadedForUserId` and would otherwise stay stale).
  let sheetWasOpen = false;
  $: if (sheetOpen && !sheetWasOpen) {
    sheetWasOpen = true;
    void refreshCyclePreference();
  } else if (!sheetOpen && sheetWasOpen) {
    sheetWasOpen = false;
  }

  // A widget deep link on a already-running, already-authenticated app only
  // changes the URL — the auth subscription in onMount never re-fires, so the
  // sheet would stay closed without this (#447). Navigation changes $page, and
  // the param is stripped once handled, so this runs at most once per link.
  $: if ($page.url && isOpenEntryRequested($page.url.searchParams)) {
    void maybeOpenFromQuery();
  }
  $: if (!sheetOpen && $entrySheetStore.open) {
    sheetOpen = true;
  }

  function stripOpenEntryQuery(): void {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (!isOpenEntryRequested(url.searchParams)) return;
    url.searchParams.delete('openEntry');
    url.searchParams.delete('date');
    history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }

  async function maybeOpenFromQuery(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    // Cold start fires this from the auth subscription while a warm deep link
    // fires it from the navigation below; both can race on the same param.
    if (openFromQueryPending) return;
    openFromQueryPending = true;
    try {
      await openFromQuery();
    } finally {
      openFromQueryPending = false;
    }
  }

  async function openFromQuery(): Promise<void> {
    const params =
      typeof window !== 'undefined'
        ? new URL(window.location.href).searchParams
        : $page.url.searchParams;
    if (!isOpenEntryRequested(params)) return;
    // isoDate is device-local (same as Home "+"); widget deep links omit date.
    const date = entryDateFromSearchParams(params) ?? isoDate(new Date());
    let onboardingTags = false;
    try {
      const [preferences, summary] = await Promise.all([
        fetchUserPreferences(),
        fetchDashboardSummary(date),
      ]);
      const hasStash = hasOnboardingSuggestionStash(preferences.user_id);
      // Onboarding not finished yet (and no offline-deferred stash to finalize
      // inside the sheet) → run the full /onboarding sequence first instead of
      // opening the tag-embed entry.
      if (
        shouldRedirectToOnboarding(preferences, summary.entry_count, {
          hasDeferredSuggestionStash: hasStash,
        })
      ) {
        stripOpenEntryQuery();
        await goto('/onboarding');
        return;
      }
      onboardingTags = shouldShowOnboardingTags(preferences, summary.entry_count, {
        hasDeferredSuggestionStash: hasStash,
      });
    } catch {
      // Offline / API blip: preferences+summary rejected, but a deferred
      // suggestion stash (offline wizard finish) must still enable the entry's
      // deferred-finalize path — otherwise the first entry saves with onboarding
      // left incomplete. Read the stash independently of the API.
      const state = get(auth);
      const userId = state.status === 'authenticated' ? state.user.id : null;
      onboardingTags = userId ? hasOnboardingSuggestionStash(userId) : false;
    }
    openEntrySheet(date, { onboardingTags });
    stripOpenEntryQuery();
  }

  async function loadProfileDefault(): Promise<void> {
    const state = get(auth);
    if (state.status !== 'authenticated') return;
    const userId = state.user.id;
    // Skip only when this account's defaults are already cached. login()/setUser()
    // can move A→B while staying `authenticated` (no anonymous gap), so a boolean
    // `profileLoaded` would leave A's work_context_typical in place and autosave
    // it into B's new entries.
    if (profileLoadedForUserId === userId) return;
    profileLoadedForUserId = userId;
    // Drop prior-account defaults before the await so a slow profile fetch cannot
    // keep painting A's typical onto B's sheet.
    workContextTypical = null;
    cycleTrackingEnabled = true;
    // allSettled: a transient /user/preferences failure must not discard a
    // successfully loaded work-context profile default (and vice versa).
    const [profileRes, prefRes] = await Promise.allSettled([
      fetchUserProfile(),
      fetchUserPreferences(),
    ]);
    // Another account may have won the race while we awaited.
    const latest = get(auth);
    if (latest.status !== 'authenticated' || latest.user.id !== userId) return;
    if (profileRes.status === 'fulfilled') {
      workContextTypical = profileRes.value.work_context_typical ?? null;
    }
    if (prefRes.status === 'fulfilled') {
      cycleTrackingEnabled = prefRes.value.cycle_tracking_enabled;
    }
  }

  async function refreshCyclePreference(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    try {
      const preferences = await fetchUserPreferences();
      cycleTrackingEnabled = preferences.cycle_tracking_enabled;
    } catch {
      // Keep the last known value when preferences are unreachable.
    }
  }

  function handleSheetClose(): void {
    closeEntrySheet();
    sheetOpen = false;
  }

  onMount(() => {
    const unsubscribeAuth = auth.subscribe((state) => {
      if (state.status !== 'authenticated') {
        closeEntrySheet();
        sheetOpen = false;
        workContextTypical = null;
        cycleTrackingEnabled = true;
        profileLoadedForUserId = null;
        return;
      }
      void loadProfileDefault();
      void maybeOpenFromQuery();
    });

    const unsubscribePage = page.subscribe(() => {
      void maybeOpenFromQuery();
    });

    void maybeOpenFromQuery();

    return () => {
      unsubscribeAuth();
      unsubscribePage();
    };
  });
</script>

{#if $auth.status === 'authenticated'}
  <EntrySheet
    bind:open={sheetOpen}
    initialDate={$entrySheetStore.date}
    onboardingTagsEnabled={$entrySheetStore.onboardingTagsEnabled}
    {workContextTypical}
    {cycleTrackingEnabled}
    on:close={handleSheetClose}
    on:saved={() => notifyEntrySheetSaved()}
  />
{/if}
