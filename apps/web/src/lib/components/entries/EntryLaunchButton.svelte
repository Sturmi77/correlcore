<script lang="ts">
  import { openEntrySheet } from '$lib/stores/entrySheet';
  import type { EntryNavigationDate } from '$lib/navigation/openEntry';

  export let date: EntryNavigationDate | undefined = undefined;
  export let className = 'btn btn-sm variant-soft-primary';

  function openEntry(): void {
    openEntrySheet(date);
  }
</script>

<button type="button" class={className} on:click={openEntry}>
  <slot />
</button>
