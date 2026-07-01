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
  import { entryDateFromSearchParams, isOpenEntryRequested } from '$lib/navigation/openEntry';
  import { isoDate } from '$lib/utils/entryForm';
  import { shouldShowOnboardingTags } from '$lib/utils/onboardingEntry';
  import EntrySheet from './EntrySheet.svelte';

  let sheetOpen = false;

  $: sheetOpen = $entrySheetStore.open;
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
    const params =
      typeof window !== 'undefined'
        ? new URL(window.location.href).searchParams
        : $page.url.searchParams;
    if (!isOpenEntryRequested(params)) return;
    const date = entryDateFromSearchParams(params) ?? isoDate(new Date());
    let onboardingTags = false;
    try {
      const [preferences, summary] = await Promise.all([
        fetchUserPreferences(),
        fetchDashboardSummary(date),
      ]);
      onboardingTags = shouldShowOnboardingTags(preferences, summary.entry_count);
    } catch {
      onboardingTags = false;
    }
    openEntrySheet(date, { onboardingTags });
    stripOpenEntryQuery();
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
        return;
      }
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
    on:close={handleSheetClose}
    on:saved={() => notifyEntrySheetSaved()}
  />
{/if}
