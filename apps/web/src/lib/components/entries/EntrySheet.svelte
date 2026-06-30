<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import EntryForm from '$lib/components/entries/EntryForm.svelte';

  export let open = false;
  export let initialDate: string;
  export let onboardingTagsEnabled = false;

  const dispatch = createEventDispatcher<{ close: void; saved: void }>();

  let panelEl: HTMLDivElement | null = null;
  let entryForm: EntryForm;
  let returnFocusEl: HTMLElement | null = null;

  async function close() {
    const ok = entryForm ? await entryForm.requestClose() : true;
    if (ok) handleFormClose();
  }

  function onBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      void close();
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (!open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      void close();
    }
  }

  function handleFormClose() {
    open = false;
    dispatch('close');
  }

  function handleFormSaved() {
    dispatch('saved');
  }

  $: if (open && typeof document !== 'undefined') {
    returnFocusEl = document.activeElement as HTMLElement | null;
    document.body.style.overflow = 'hidden';
    queueMicrotask(() => {
      const focusTarget =
        panelEl?.querySelector<HTMLElement>('#entry-mood') ??
        panelEl?.querySelector<HTMLElement>('button, [href], input, select, textarea');
      focusTarget?.focus();
    });
  } else if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
    if (returnFocusEl) {
      returnFocusEl.focus();
      returnFocusEl = null;
    }
  }

  onDestroy(() => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
    }
  });
</script>

<svelte:window on:keydown={onKeydown} />

{#if open}
  <div
    class="entry-sheet-backdrop"
    role="presentation"
    data-testid="entry-sheet-backdrop"
    on:click={onBackdropClick}
    on:keydown={() => {}}
  >
    <div
      class="entry-sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="entry-sheet-title"
      data-testid="entry-sheet"
      bind:this={panelEl}
    >
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
      {#key initialDate}
        <div class="entry-sheet__body">
          <EntryForm
            bind:this={entryForm}
            mode="sheet"
            {initialDate}
            {onboardingTagsEnabled}
            on:close={handleFormClose}
            on:saved={handleFormSaved}
          />
        </div>
      {/key}
    </div>
  </div>
{/if}

<style>
  .entry-sheet-backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    background: color-mix(in oklch, var(--color-bg) 55%, transparent);
    padding: 0;
  }

  .entry-sheet {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: var(--content-max-width);
    max-height: min(92dvh, 720px);
    margin: 0 auto;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-bottom: none;
    box-shadow: 0 -8px 32px color-mix(in oklch, var(--color-bg) 30%, transparent);
    overflow: hidden;
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
    width: 2.75rem;
    height: 2.75rem;
    border: none;
    border-radius: var(--radius-full);
    background: var(--color-surface-2);
    color: var(--color-fg);
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
  }

  .entry-sheet__body {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-4);
    padding-top: var(--space-6);
    padding-bottom: calc(var(--space-6) + env(safe-area-inset-bottom));
  }

  @media (min-width: 768px) {
    .entry-sheet-backdrop {
      align-items: center;
      padding: var(--space-6);
    }

    .entry-sheet {
      max-height: min(88dvh, 800px);
      border-radius: var(--radius-lg);
      border-bottom: 1px solid var(--color-border);
    }

    .entry-sheet__handle {
      display: none;
    }
  }
</style>
