<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
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
  import { shouldShowOnboardingTags } from '$lib/utils/onboardingEntry';
  import { hasOnboardingSuggestionStash } from '$lib/utils/onboardingSuggestionStash';
  import { shouldShowMaturityExpectationIntro } from '$lib/utils/maturityExpectationIntro';
  import EntrySheet from './EntrySheet.svelte';

  let sheetOpen = false;
  let workContextTypical: WorkContextTypical | null = null;
  let profileLoaded = false;
  let openFromQueryPending = false;

  $: sheetOpen = $entrySheetStore.open;

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
      // Defer to Home: maturity expectation runs before first-entry tags.
      if (
        shouldShowMaturityExpectationIntro({
          preferences,
          entryCount: summary.entry_count,
          entrySheetOpen: false,
        })
      ) {
        stripOpenEntryQuery();
        return;
      }
      onboardingTags = shouldShowOnboardingTags(preferences, summary.entry_count, {
        hasDeferredSuggestionStash: hasOnboardingSuggestionStash(preferences.user_id),
      });
    } catch {
      onboardingTags = false;
    }
    openEntrySheet(date, { onboardingTags });
    stripOpenEntryQuery();
  }

  async function loadProfileDefault(): Promise<void> {
    if (profileLoaded || get(auth).status !== 'authenticated') return;
    profileLoaded = true;
    try {
      const profile = await fetchUserProfile();
      workContextTypical = profile.work_context_typical ?? null;
    } catch {
      workContextTypical = null;
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
        profileLoaded = false;
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
    on:close={handleSheetClose}
    on:saved={() => notifyEntrySheetSaved()}
  />
{/if}
