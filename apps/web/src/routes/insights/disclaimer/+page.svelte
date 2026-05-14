<script lang="ts">
  /**
   * /insights/disclaimer — Correlation Disclaimer page (M3.1, TODO-2)
   *
   * Renders CorrelationDisclaimer full-screen (open=true by default).
   * On close (Escape / backdrop / got-it) navigates back to /insights.
   *
   * This page exists so the href="/insights/disclaimer" link in InsightCard
   * does not result in a 404. On mobile the disclaimer slides up as a bottom
   * sheet; on desktop it appears as a centred modal (handled inside the
   * component via CSS media query).
   */
  import { goto } from '$app/navigation';
  import { _ } from 'svelte-i18n';
  import CorrelationDisclaimer from '$lib/components/insights/CorrelationDisclaimer.svelte';

  let open = true;

  function handleClose() {
    open = false;
    void goto('/insights');
  }
</script>

<svelte:head>
  <title
    >{$_('insights.disclaimer.page_title', { default: 'Correlation Disclaimer' })} - {$_(
      'app.name'
    )}</title
  >
</svelte:head>

<!--
  Minimal page shell — the CorrelationDisclaimer renders its own
  backdrop and modal container via position:fixed, so no additional
  layout wrapper is needed here.
-->
<div class="disclaimer-page" aria-hidden={!open}>
  <CorrelationDisclaimer {open} on:close={handleClose} />

  <!-- Visible only when modal is not open (e.g. after close animation
       completes before navigation fires). Acts as a safe fallback. -->
  {#if !open}
    <div class="disclaimer-page__fallback">
      <a class="btn btn-sm variant-ghost-surface" href="/insights">
        {$_('nav.back', { default: '← Back' })}
      </a>
    </div>
  {/if}
</div>

<style>
  .disclaimer-page {
    min-height: 100dvh;
    background: var(--color-bg);
  }

  .disclaimer-page__fallback {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-8);
  }
</style>
