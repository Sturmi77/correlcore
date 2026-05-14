<script lang="ts">
  /**
   * CorrelationDisclaimer — Issue #168, FRONTEND.md §1.4
   *
   * Bottom sheet (mobile) / modal (desktop) explaining correlation ≠ causation.
   * Triggered by the ⓘ link on InsightCard and the InsightFeed page header.
   *
   * Props
   * -----
   * open   boolean  Controls visibility; bind:open to toggle from parent
   *
   * Events
   * ------
   * close  Dispatched when the user closes the modal (Escape, backdrop, close button)
   */
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';

  export let open = false;

  const dispatch = createEventDispatcher<{ close: void }>();

  let dialogEl: HTMLDialogElement | null = null;
  let firstFocusable: HTMLElement | null = null;
  let lastFocusable: HTMLElement | null = null;

  const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function updateFocusBounds() {
    if (!dialogEl) return;
    const nodes = Array.from(dialogEl.querySelectorAll<HTMLElement>(FOCUSABLE));
    firstFocusable = nodes[0] ?? null;
    lastFocusable = nodes[nodes.length - 1] ?? null;
  }

  function trapFocus(e: KeyboardEvent) {
    if (e.key !== 'Tab') return;
    if (!firstFocusable || !lastFocusable) return;
    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      }
    } else {
      if (document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
    else trapFocus(e);
  }

  function close() {
    dispatch('close');
  }

  function onBackdrop(e: MouseEvent) {
    if (e.target === dialogEl) close();
  }

  let previouslyFocused: HTMLElement | null = null;

  $: if (open) {
    previouslyFocused = document.activeElement as HTMLElement;
    // defer so the DOM is painted before we focus
    setTimeout(() => {
      updateFocusBounds();
      firstFocusable?.focus();
    }, 0);
  } else {
    previouslyFocused?.focus();
    previouslyFocused = null;
  }

  onMount(() => {
    document.addEventListener('keydown', onKeydown);
  });

  onDestroy(() => {
    document.removeEventListener('keydown', onKeydown);
  });
</script>

{#if open}
  <div class="cd-backdrop" role="presentation" on:click={onBackdrop} data-testid="cd-backdrop">
    <div
      bind:this={dialogEl}
      class="cd-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cd-title"
      data-testid="cd-modal"
    >
      <div class="cd-header">
        <h2 id="cd-title" class="cd-title" data-testid="cd-title">
          {$_('insights.disclaimer.modal_title')}
        </h2>
        <button
          class="cd-close"
          aria-label={$_('insights.disclaimer.close_aria')}
          data-testid="cd-close"
          on:click={close}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div class="cd-body" data-testid="cd-body">
        <!-- Section 1: What is a correlation? -->
        <section class="cd-section" data-testid="cd-section-1">
          <h3 class="cd-section-title">
            {$_('insights.disclaimer.section1_title')}
          </h3>
          <p class="cd-section-body">
            {$_('insights.disclaimer.section1_body')}
          </p>
        </section>

        <!-- Section 2: Confidence bar -->
        <section class="cd-section" data-testid="cd-section-2">
          <h3 class="cd-section-title">
            {$_('insights.disclaimer.section2_title')}
          </h3>
          <p class="cd-section-body">
            {$_('insights.disclaimer.section2_body')}
          </p>
        </section>

        <!-- Section 3: Minimum data requirement -->
        <section class="cd-section" data-testid="cd-section-3">
          <h3 class="cd-section-title">
            {$_('insights.disclaimer.section3_title')}
          </h3>
          <p class="cd-section-body">
            {$_('insights.disclaimer.section3_body')}
          </p>
        </section>

        <!-- Section 4: Statistical methods -->
        <section class="cd-section" data-testid="cd-section-4">
          <h3 class="cd-section-title">
            {$_('insights.disclaimer.section4_title')}
          </h3>
          <p class="cd-section-body">
            {$_('insights.disclaimer.section4_body')}
          </p>
        </section>
      </div>

      <div class="cd-footer">
        <button class="cd-got-it" data-testid="cd-got-it" on:click={close}>
          {$_('insights.disclaimer.got_it')}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .cd-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: oklch(from var(--color-text) l c h / 0.45);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 0;
    animation: cdFadeIn 160ms ease both;
  }

  @keyframes cdFadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .cd-modal {
    background: var(--color-surface);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: var(--shadow-lg);
    width: 100%;
    max-width: 560px;
    max-height: 88dvh;
    overflow-y: auto;
    overscroll-behavior: contain;
    display: flex;
    flex-direction: column;
    animation: cdSlideUp 220ms cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  @keyframes cdSlideUp {
    from {
      transform: translateY(20px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  /* Desktop: centred dialog instead of bottom-sheet */
  @media (min-width: 640px) {
    .cd-backdrop {
      align-items: center;
      padding: var(--space-4);
    }
    .cd-modal {
      border-radius: var(--radius-xl);
      max-height: 80dvh;
    }
  }

  .cd-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-5) var(--space-5) var(--space-3);
    border-bottom: 1px solid oklch(from var(--color-text) l c h / 0.08);
    position: sticky;
    top: 0;
    background: var(--color-surface);
    z-index: 1;
  }

  .cd-title {
    flex: 1;
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0;
    line-height: 1.3;
    color: var(--color-text);
  }

  .cd-close {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    transition:
      color var(--transition-interactive),
      background var(--transition-interactive);
  }

  .cd-close:hover,
  .cd-close:focus-visible {
    color: var(--color-text);
    background: var(--color-surface-offset);
  }

  .cd-body {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-5);
    overflow-y: auto;
  }

  .cd-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .cd-section-title {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  .cd-section-body {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    line-height: 1.6;
    margin: 0;
    max-width: 62ch;
  }

  .cd-footer {
    padding: var(--space-4) var(--space-5) var(--space-6);
    border-top: 1px solid oklch(from var(--color-text) l c h / 0.08);
    position: sticky;
    bottom: 0;
    background: var(--color-surface);
  }

  .cd-got-it {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    background: var(--color-primary);
    color: var(--color-text-inverse);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 600;
    transition: background var(--transition-interactive);
  }

  .cd-got-it:hover,
  .cd-got-it:focus-visible {
    background: var(--color-primary-hover);
  }

  @media (prefers-reduced-motion: reduce) {
    .cd-backdrop,
    .cd-modal {
      animation: none;
    }
  }
</style>
