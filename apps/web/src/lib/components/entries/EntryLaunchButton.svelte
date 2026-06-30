<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolveEntryPath } from '$lib/navigation/entryNavigation';
  import type { EntryNavigationDate } from '$lib/navigation/openEntry';

  export let date: EntryNavigationDate | undefined = undefined;
  export let className = 'btn btn-sm variant-soft-primary';

  function openEntry(): void {
    void goto(resolveEntryPath(date));
  }
</script>

<button type="button" class={className} on:click={openEntry}>
  <slot />
</button>
