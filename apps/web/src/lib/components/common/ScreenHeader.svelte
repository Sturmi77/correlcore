<script lang="ts">
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
</script>

<header
  class="screen-header"
  class:screen-header--compact={compact}
  class:screen-header--visually-hidden={visuallyHidden}
>
  {#if back}
    <a class="screen-header__back" href={back.href} data-testid="screen-back">
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
