<script lang="ts">
  export let title: string;
  export let subtitle = '';
  export let eyebrow = '';
  export let compact = false;
</script>

<header class="screen-header" class:screen-header--compact={compact}>
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
</header>

<style>
  .screen-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
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

  @media (max-width: 520px) {
    .screen-header {
      flex-direction: column;
      align-items: stretch;
    }

    .screen-header__actions {
      justify-content: flex-start;
    }
  }
</style>
