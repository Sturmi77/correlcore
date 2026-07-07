<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { buildOpenEntryPath } from '$lib/navigation/openEntry';
  import { resolveInitialDate } from '$lib/utils/entryForm';

  const initialDate = resolveInitialDate(new Date(), get(page).url.searchParams.get('date'));

  onMount(() => {
    void goto(buildOpenEntryPath(initialDate), { replaceState: true });
  });
</script>

<svelte:head>
  <title>{$_('entry.title')} - {$_('app.name')}</title>
</svelte:head>
