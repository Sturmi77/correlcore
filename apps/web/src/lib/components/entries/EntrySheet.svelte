<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { WorkContextTypical } from '$lib/api/profile';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import EntryForm from '$lib/components/entries/EntryForm.svelte';
  import { currentUser } from '$lib/stores/auth';
  import { getEntryOpenMode, type EntryOpenMode } from '$lib/utils/entryOpenMode';

  export let open = false;
  export let initialDate: string;
  export let onboardingTagsEnabled = false;
  export let workContextTypical: WorkContextTypical | null = null;
  export let cycleTrackingEnabled = true;

  const dispatch = createEventDispatcher<{ close: void; saved: void }>();

  let entryForm: EntryForm;
  let openMode: EntryOpenMode = 'full';

  // Remount when the authenticated account changes without an anonymous gap
  // (login/setUser A→B). Otherwise the prior user's hydrated mood/note/
  // existingEntryId stay in the closed sheet and can autosave into B.
  $: entryFormRemountKey = `${$currentUser?.id ?? ''}:${initialDate}`;

  $: if (open) {
    openMode = getEntryOpenMode();
  }

  async function close() {
    const ok = entryForm ? await entryForm.requestClose() : true;
    if (ok) handleFormClose();
  }

  function handleFormClose() {
    open = false;
    dispatch('close');
  }

  function handleFormSaved() {
    dispatch('saved');
  }
</script>

<BottomSheet
  {open}
  labelledBy="entry-sheet-title"
  testId="entry-sheet"
  closeAriaLabel={$_('entry.sheet.close')}
  on:close={() => void close()}
>
  <div class="entry-sheet">
    <div class="entry-sheet__handle" aria-hidden="true"></div>
    <button
      type="button"
      class="entry-sheet__close"
      aria-label={$_('entry.sheet.close')}
      data-testid="entry-sheet-close"
      on:click={() => void close()}
    >
      ×
    </button>
    {#key entryFormRemountKey}
      <div class="entry-sheet__body">
        <EntryForm
          bind:this={entryForm}
          mode="sheet"
          {initialDate}
          {openMode}
          {onboardingTagsEnabled}
          {workContextTypical}
          {cycleTrackingEnabled}
          on:close={handleFormClose}
          on:saved={handleFormSaved}
        />
      </div>
    {/key}
  </div>
</BottomSheet>

<style>
  .entry-sheet {
    position: relative;
    display: flex;
    flex-direction: column;
    margin: calc(-1 * var(--space-4));
    margin-bottom: calc(-1 * (var(--space-4) + env(safe-area-inset-bottom)));
    max-height: min(82dvh, 42rem);
    overflow: hidden;
    background: var(--color-bg);
  }

  @media (min-width: 768px) {
    .entry-sheet {
      margin-bottom: calc(-1 * var(--space-4));
      max-height: min(88dvh, 800px);
    }
  }

  .entry-sheet__handle {
    flex-shrink: 0;
    width: 2.5rem;
    height: 0.25rem;
    margin: var(--space-2) auto 0;
    border-radius: var(--radius-full);
    background: var(--color-border);
  }

  .entry-sheet__close {
    position: absolute;
    top: var(--space-2);
    right: var(--space-3);
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    width: var(--tap-target);
    height: var(--tap-target);
    border: none;
    border-radius: var(--radius-full);
    background: var(--color-surface-2);
    color: var(--color-fg);
    font-size: var(--text-xl);
    line-height: 1;
    cursor: pointer;
  }

  .entry-sheet__body {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-4);
    padding-bottom: calc(var(--space-4) + env(safe-area-inset-bottom));
  }

  @media (max-width: 767px) {
    .entry-sheet__body {
      padding-inline: var(--space-3);
      padding-top: var(--space-3);
      padding-bottom: calc(var(--space-3) + env(safe-area-inset-bottom));
    }
  }

  @media (min-width: 768px) {
    .entry-sheet__handle {
      display: none;
    }
  }
</style>
