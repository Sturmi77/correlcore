<script lang="ts">
  /**
   * CorrelationDisclaimer — Issue #168, FRONTEND.md §1.4
   *
   * Bottom sheet (mobile) / modal (desktop) explaining correlation ≠ causation.
   * Triggered by the ⓘ link on InsightCard and the InsightFeed page header.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';

  export let open = false;

  const dispatch = createEventDispatcher<{ close: void }>();

  function close() {
    dispatch('close');
  }
</script>

<BottomSheet
  {open}
  labelledBy="cd-title"
  testId="cd-backdrop"
  closeAriaLabel={$_('insights.disclaimer.close_aria')}
  on:close={close}
>
  <div class="cd-modal" data-testid="cd-modal">
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
      <section class="cd-section" data-testid="cd-section-1">
        <h3 class="cd-section-title">
          {$_('insights.disclaimer.section1_title')}
        </h3>
        <p class="cd-section-body">
          {$_('insights.disclaimer.section1_body')}
        </p>
      </section>

      <section class="cd-section" data-testid="cd-section-2">
        <h3 class="cd-section-title">
          {$_('insights.disclaimer.section2_title')}
        </h3>
        <p class="cd-section-body">
          {$_('insights.disclaimer.section2_body')}
        </p>
      </section>

      <section class="cd-section" data-testid="cd-section-3">
        <h3 class="cd-section-title">
          {$_('insights.disclaimer.section3_title')}
        </h3>
        <p class="cd-section-body">
          {$_('insights.disclaimer.section3_body')}
        </p>
      </section>

      <section class="cd-section" data-testid="cd-section-4">
        <h3 class="cd-section-title">
          {$_('insights.disclaimer.section4_title')}
        </h3>
        <p class="cd-section-body">
          {$_('insights.disclaimer.section4_body')}
        </p>
      </section>

      <section class="cd-section" data-testid="cd-section-5">
        <h3 class="cd-section-title">
          {$_('insights.disclaimer.section5_title')}
        </h3>
        <p class="cd-section-body">
          {$_('insights.disclaimer.section5_body')}
        </p>
      </section>
    </div>

    <div class="cd-footer">
      <button class="cd-got-it" data-testid="cd-got-it" on:click={close}>
        {$_('insights.disclaimer.got_it')}
      </button>
    </div>
  </div>
</BottomSheet>

<style>
  .cd-modal {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin: calc(-1 * var(--space-4));
    margin-bottom: calc(-1 * (var(--space-4) + env(safe-area-inset-bottom)));
    max-height: min(82dvh, 42rem);
    overflow: hidden;
  }

  @media (min-width: 768px) {
    .cd-modal {
      margin-bottom: calc(-1 * var(--space-4));
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
</style>
