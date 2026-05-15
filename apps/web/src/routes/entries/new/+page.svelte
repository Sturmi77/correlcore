<script lang="ts">
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import EntryForm from '$lib/components/entries/EntryForm.svelte';
  import { resolveInitialDate } from '$lib/utils/entryForm';

  const initialDate = resolveInitialDate(new Date(), get(page).url.searchParams.get('date'));
</script>

<svelte:head>
  <title>{$_('entry.title')} — {$_('app.name')}</title>
</svelte:head>

<EntryForm mode="page" {initialDate} />
