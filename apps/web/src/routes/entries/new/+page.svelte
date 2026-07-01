<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import EntryForm from '$lib/components/entries/EntryForm.svelte';
  import { buildOpenEntryPath } from '$lib/navigation/openEntry';
  import { prefersEntrySheet } from '$lib/navigation/entryNavigation';
  import { resolveInitialDate } from '$lib/utils/entryForm';

  const initialDate = resolveInitialDate(new Date(), get(page).url.searchParams.get('date'));
  let allowPage = false;

  onMount(() => {
    if (prefersEntrySheet()) {
      void goto(buildOpenEntryPath(initialDate), { replaceState: true });
      return;
    }
    allowPage = true;
  });
</script>

<svelte:head>
  <title>{$_('entry.title')} — {$_('app.name')}</title>
</svelte:head>

{#if allowPage}
  <EntryForm mode="page" {initialDate} />
{/if}
