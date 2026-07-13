<script context="module" lang="ts">
  export type InlineAlertVariant = 'info' | 'success' | 'warning' | 'error';
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './Button.svelte';

  export let variant: InlineAlertVariant = 'info';
  export let message: string;
  export let actionLabel = '';
  export let actionTestId = '';
  export let testId: string | undefined = undefined;

  const dispatch = createEventDispatcher<{ action: void }>();

  $: role = variant === 'error' ? 'alert' : 'status';
  $: actionDataTestId = actionTestId || (testId ? `${testId}-action` : undefined);
</script>

<div class="inline-alert inline-alert--{variant}" {role} data-testid={testId}>
  <span>{message}</span>
  {#if actionLabel}
    <Button
      variant={variant === 'error' ? 'danger' : 'secondary'}
      size="sm"
      data-testid={actionDataTestId}
      on:click={() => dispatch('action')}
    >
      {actionLabel}
    </Button>
  {/if}
</div>

<style>
  .inline-alert {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--text-sm);
  }

  .inline-alert--info {
    border-color: color-mix(in srgb, var(--color-primary) 22%, transparent);
    background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
  }

  .inline-alert--success {
    border-color: color-mix(in srgb, var(--color-success) 24%, transparent);
    background: color-mix(in srgb, var(--color-success) 8%, var(--color-surface));
  }

  .inline-alert--warning {
    border-color: color-mix(in srgb, var(--color-warning) 24%, transparent);
    background: color-mix(in srgb, var(--color-warning) 10%, var(--color-surface));
  }

  .inline-alert--error {
    border-color: color-mix(in srgb, var(--color-error) 26%, transparent);
    background: var(--color-error-highlight);
    color: var(--color-error);
  }

  @media (max-width: 480px) {
    .inline-alert {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
