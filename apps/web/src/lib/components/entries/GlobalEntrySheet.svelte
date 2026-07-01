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
  import {
    entryDateFromSearchParams,
    isOpenEntryRequested,
  } from '$lib/navigation/openEntry';
  import { isoDate } from '$lib/utils/entryForm';
  import EntrySheet from './EntrySheet.svelte';

  let sheetOpen = false;
  let openEntryHandled = false;

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

  function maybeOpenFromQuery(): void {
    if (get(auth).status !== 'authenticated' || openEntryHandled) return;
    const params =
      typeof window !== 'undefined'
        ? new URL(window.location.href).searchParams
        : $page.url.searchParams;
    if (!isOpenEntryRequested(params)) return;
    openEntryHandled = true;
    const date = entryDateFromSearchParams(params) ?? isoDate(new Date());
    openEntrySheet(date);
    stripOpenEntryQuery();
  }

  function handleSheetClose(): void {
    closeEntrySheet();
    sheetOpen = false;
  }

  onMount(() => {
    const unsubscribeAuth = auth.subscribe((state) => {
      if (state.status !== 'authenticated') {
        openEntryHandled = false;
        closeEntrySheet();
        sheetOpen = false;
        return;
      }
      maybeOpenFromQuery();
    });

    const unsubscribePage = page.subscribe(() => {
      maybeOpenFromQuery();
    });

    maybeOpenFromQuery();

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
