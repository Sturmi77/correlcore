<script context="module" lang="ts">
  export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'link';
  export type ButtonSize = 'sm' | 'md' | 'lg';
</script>

<script lang="ts">
  export let href: string | undefined = undefined;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let variant: ButtonVariant = 'secondary';
  export let size: ButtonSize = 'md';
  export let fullWidth = false;
  export let stacked = false;
  export let iconOnly = false;
  export let disabled = false;
  export let loading = false;
  export let className = '';

  $: classes = [
    'ui-button',
    `ui-button--${variant}`,
    `ui-button--${size}`,
    fullWidth ? 'ui-button--full' : '',
    stacked ? 'ui-button--stacked' : '',
    iconOnly ? 'ui-button--icon-only' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');
</script>

{#if href}
  <a
    {...$$restProps}
    class={classes}
    {href}
    aria-disabled={disabled || loading ? 'true' : undefined}
    aria-busy={loading ? 'true' : undefined}
    data-loading={loading ? 'true' : undefined}
    on:click
  >
    {#if loading}<span class="ui-button__spinner" aria-hidden="true"></span>{/if}
    <slot />
  </a>
{:else}
  <button
    {...$$restProps}
    class={classes}
    {type}
    disabled={disabled || loading}
    aria-busy={loading ? 'true' : undefined}
    data-loading={loading ? 'true' : undefined}
    on:click
  >
    {#if loading}<span class="ui-button__spinner" aria-hidden="true"></span>{/if}
    <slot />
  </button>
{/if}

<style>
  .ui-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    min-width: 44px;
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    color: var(--color-text);
    font-weight: 650;
    line-height: 1.2;
    text-align: center;
    text-decoration: none;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive),
      color var(--transition-interactive),
      opacity var(--transition-interactive);
  }

  .ui-button:disabled,
  .ui-button[aria-disabled='true'] {
    cursor: not-allowed;
    opacity: 0.56;
  }

  .ui-button--sm {
    min-height: 44px;
    padding: 0.375rem 0.625rem;
    font-size: var(--text-sm);
  }

  .ui-button--md {
    font-size: var(--text-sm);
  }

  .ui-button--lg {
    min-height: 3.75rem;
    padding: var(--space-4);
    font-size: var(--text-base);
  }

  .ui-button--full {
    width: 100%;
  }

  .ui-button--stacked {
    flex-direction: column;
    gap: var(--space-1);
  }

  .ui-button--icon-only {
    width: 44px;
    padding-inline: 0;
  }

  .ui-button--primary {
    border-color: color-mix(in oklch, var(--color-primary) 22%, transparent);
    background: var(--color-primary);
    color: var(--color-text-inverse);
  }

  .ui-button--secondary {
    border-color: color-mix(in srgb, var(--color-primary) 24%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
    color: var(--color-primary);
  }

  .ui-button--ghost {
    border-color: color-mix(in srgb, currentColor 12%, transparent);
    background: color-mix(in srgb, currentColor 6%, transparent);
    color: var(--color-text);
  }

  .ui-button--danger {
    border-color: color-mix(in srgb, var(--color-error) 28%, transparent);
    background: color-mix(in srgb, var(--color-error) 12%, var(--color-surface));
    color: var(--color-error);
  }

  .ui-button--link {
    min-height: 44px;
    border-color: transparent;
    background: transparent;
    color: var(--color-primary);
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .ui-button__spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: var(--radius-full);
    animation: ui-button-spin 700ms linear infinite;
  }

  @keyframes ui-button-spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (hover: hover) {
    .ui-button:not(:disabled):not([aria-disabled='true']):hover {
      border-color: color-mix(in srgb, currentColor 24%, transparent);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .ui-button,
    .ui-button__spinner {
      transition: none;
      animation: none;
    }
  }
</style>
