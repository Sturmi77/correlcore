<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { browser } from '$app/environment';

  /** Controls visibility; when true the dialog is shown modally. */
  export let open = false;
  /** ID of the element that labels the dialog (usually the sheet title). */
  export let labelledBy: string;
  export let testId = 'bottom-sheet';
  export let closeAriaLabel: string;

  const dispatch = createEventDispatcher<{ close: void }>();

  let dialog: HTMLDialogElement;

  function requestClose(): void {
    dispatch('close');
  }

  function openDialog(): void {
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
      return;
    }
    dialog.setAttribute('open', '');
  }

  function closeDialog(): void {
    if (typeof dialog.close === 'function') {
      dialog.close();
      return;
    }
    dialog.removeAttribute('open');
  }

  function syncDialog(shouldOpen: boolean): void {
    if (!browser || !dialog) return;
    if (shouldOpen && !dialog.open) {
      openDialog();
      return;
    }
    if (!shouldOpen && dialog.open) {
      closeDialog();
    }
  }

  $: if (browser && dialog) syncDialog(open);

  function onDialogClick(event: MouseEvent): void {
    if (event.target === dialog) requestClose();
  }
</script>

{#if open}
  <dialog
    bind:this={dialog}
    class="bottom-sheet"
    aria-labelledby={labelledBy}
    data-testid={testId}
    data-ptr-ignore
    on:click={onDialogClick}
    on:close={requestClose}
    on:cancel|preventDefault={requestClose}
  >
    <button
      type="button"
      class="bottom-sheet__sr-close"
      aria-label={closeAriaLabel}
      tabindex="-1"
      on:click={requestClose}
    ></button>
    <div class="bottom-sheet__panel">
      <slot />
    </div>
  </dialog>
{/if}

<style>
  .bottom-sheet {
    margin: 0;
    padding: 0;
    border: none;
    width: 100%;
    max-width: 100%;
    height: 100%;
    max-height: 100%;
    background: transparent;
    overflow: hidden;
  }

  .bottom-sheet::backdrop {
    background: var(--color-scrim);
  }

  .bottom-sheet__sr-close {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .bottom-sheet__panel {
    position: fixed;
    inset-inline: 0;
    bottom: 0;
    margin-inline: auto;
    width: min(100%, 42rem);
    max-height: min(82dvh, 42rem);
    overflow: auto;
    padding: var(--space-4);
    padding-bottom: calc(var(--space-4) + env(safe-area-inset-bottom));
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-bottom: 0;
    box-shadow: var(--shadow-lg);
    overscroll-behavior: contain;
  }

  @media (min-width: 768px) {
    .bottom-sheet__panel {
      inset: auto;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      border-radius: var(--radius-xl);
      border-bottom: 1px solid var(--color-border);
      padding-bottom: var(--space-4);
    }
  }
</style>
