<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';

  export let title: string;
  export let subtitle = '';
  export let eyebrow = '';
  export let compact = false;
  /** Visually hide the header while keeping a single page-level h1 for a11y. */
  export let visuallyHidden = false;
  /**
   * Standardised back affordance for drill-down screens (#703). Pass a target
   * route and a human label; renders one shared ghost link instead of each
   * screen hand-rolling a raw `btn` anchor.
   */
  export let back: { href: string; label: string } | null = null;
  /**
   * Floating header mode (#703 Stage 2). When true the header is the sticky
   * screen chrome (blur/backdrop) that owns the top offset, its `controls` slot
   * carries the screen's controls (e.g. the analysis toolbars), and the title
   * copy collapses on scroll so only `[back · controls]` stays pinned.
   */
  export let sticky = false;

  let headerEl: HTMLElement | undefined;
  let scrolled = false;

  /** Nearest ancestor that actually scrolls — the shell content column, not the
   * window (see routes/+layout.svelte: `.page-shell` is `overflow-y-auto`). */
  function findScrollParent(node: HTMLElement | undefined): HTMLElement | null {
    let el = node?.parentElement ?? null;
    while (el) {
      const overflowY = getComputedStyle(el).overflowY;
      if (overflowY === 'auto' || overflowY === 'scroll') return el;
      el = el.parentElement;
    }
    return null;
  }

  onMount(() => {
    if (!sticky) return;
    const scrollParent = findScrollParent(headerEl);
    // Read from whichever actually scrolls (the shell content column normally,
    // the window as fallback) and listen on both — so a mis-detected scroll
    // parent can't leave the title stuck expanded/collapsed.
    const read = (): void => {
      const y = Math.max(scrollParent?.scrollTop ?? 0, window.scrollY);
      scrolled = y > 24;
    };
    read();
    const targets: (HTMLElement | Window)[] = scrollParent ? [scrollParent, window] : [window];
    for (const target of targets) target.addEventListener('scroll', read, { passive: true });
    return () => {
      for (const target of targets) target.removeEventListener('scroll', read);
    };
  });
</script>

<header
  bind:this={headerEl}
  class="screen-header"
  class:screen-header--compact={compact}
  class:screen-header--visually-hidden={visuallyHidden}
  class:screen-header--sticky={sticky}
  class:screen-header--scrolled={sticky && scrolled}
>
  {#if back}
    <a
      class="screen-header__back"
      href={back.href}
      data-testid="screen-back"
      aria-label={$_('nav.back_to', { values: { target: back.label } })}
    >
      <span class="screen-header__back-icon" aria-hidden="true">←</span>
      {back.label}
    </a>
  {/if}

  <div class="screen-header__row">
    <div class="screen-header__copy">
      {#if eyebrow}
        <p class="screen-header__eyebrow">{eyebrow}</p>
      {/if}
      <h1>{title}</h1>
      {#if subtitle}
        <p class="screen-header__subtitle">{subtitle}</p>
      {/if}
    </div>

    {#if $$slots.actions}
      <div class="screen-header__actions">
        <slot name="actions" />
      </div>
    {/if}
  </div>

  {#if $$slots.controls}
    <div class="screen-header__controls">
      <slot name="controls" />
    </div>
  {/if}
</header>

<style>
  .screen-header {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .screen-header__row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .screen-header__back {
    display: inline-flex;
    align-self: flex-start;
    align-items: center;
    gap: var(--space-1);
    /* 44px min touch target (FRONTEND.md contract). Horizontal padding is
     * offset by a negative inline margin so the glyph still aligns with the
     * title's left edge (#774 review). */
    min-height: 2.75rem;
    padding-inline: var(--space-1);
    margin-inline-start: calc(-1 * var(--space-1));
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 600;
    text-decoration: none;
  }

  .screen-header__back:hover {
    color: var(--color-text);
  }

  .screen-header__back-icon {
    font-size: 1em;
    line-height: 1;
  }

  .screen-header__copy {
    min-width: 0;
  }

  .screen-header__eyebrow,
  .screen-header h1,
  .screen-header__subtitle {
    margin: 0;
  }

  .screen-header__eyebrow {
    margin-bottom: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .screen-header h1 {
    color: var(--color-text);
    font-size: var(--text-xl);
    font-weight: 750;
    line-height: 1.18;
  }

  .screen-header--compact h1 {
    font-size: var(--text-lg);
  }

  .screen-header__subtitle {
    margin-top: var(--space-1);
    max-width: 42rem;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.45;
  }

  .screen-header__actions {
    display: flex;
    flex: 0 0 auto;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--space-2);
  }

  .screen-header__controls {
    min-width: 0;
  }

  /* Edge case: a page may pass the controls slot but render nothing into it
   * (e.g. Trends/Insights when logged out gate the toolbar behind auth). Svelte
   * still emits the slot wrapper (with an anchor comment), so hide it when it
   * holds no element to avoid a stray gap inside the sticky header. */
  .screen-header__controls:not(:has(*)) {
    display: none;
  }

  /* ----------------------------------------------------------------------- *
   * Floating/sticky mode (#703 Stage 2). The header becomes the screen chrome
   * that owns the top offset, so the melted-in toolbars drop their own sticky.
   * ----------------------------------------------------------------------- */
  .screen-header--sticky {
    position: sticky;
    /* Clear the device top safe-area (notch/status bar) in the Capacitor
     * edge-to-edge layout, where the shell's initial safe-area padding scrolls
     * away — otherwise the pinned controls can sit under the status bar (#774). */
    top: max(var(--space-2), env(safe-area-inset-top, 0px));
    z-index: 4;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
    backdrop-filter: blur(8px);
  }

  /* shrink-on-scroll: collapse the title copy once scrolled so only
   * [back · controls] stays pinned and content keeps the viewport. */
  .screen-header--sticky .screen-header__eyebrow,
  .screen-header--sticky .screen-header__subtitle {
    overflow: hidden;
    transition:
      max-height 0.2s ease,
      opacity 0.2s ease,
      margin 0.2s ease;
    max-height: 3rem;
  }

  .screen-header--sticky h1 {
    transition: font-size 0.2s ease;
  }

  .screen-header--scrolled .screen-header__eyebrow,
  .screen-header--scrolled .screen-header__subtitle {
    max-height: 0;
    margin: 0;
    opacity: 0;
  }

  .screen-header--scrolled h1 {
    font-size: var(--text-lg);
  }

  .screen-header--visually-hidden {
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

  @media (prefers-reduced-motion: reduce) {
    .screen-header--sticky .screen-header__eyebrow,
    .screen-header--sticky .screen-header__subtitle,
    .screen-header--sticky h1 {
      transition: none;
    }
  }

  @media (max-width: 480px) {
    .screen-header__row {
      flex-direction: column;
      align-items: stretch;
    }

    .screen-header__actions {
      justify-content: flex-start;
    }
  }
</style>
