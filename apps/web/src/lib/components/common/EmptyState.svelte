<script lang="ts">
  import Button from './Button.svelte';

  export let title: string;
  export let body = '';
  export let actionLabel = '';
  export let actionHref = '';
  export let testId: string | undefined = undefined;
</script>

<div class="empty-state" data-testid={testId}>
  {#if $$slots.icon}
    <div class="empty-state__icon" aria-hidden="true">
      <slot name="icon" />
    </div>
  {/if}
  <p class="empty-state__title">{title}</p>
  {#if body}
    <p class="empty-state__body">{body}</p>
  {/if}
  {#if actionLabel && actionHref}
    <Button
      href={actionHref}
      variant="secondary"
      size="sm"
      data-testid={testId ? `${testId}-cta` : undefined}
    >
      {actionLabel}
    </Button>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-12) var(--space-6);
    color: var(--color-text-muted);
    text-align: center;
  }

  .empty-state__icon {
    color: var(--color-text-muted);
  }

  .empty-state__title,
  .empty-state__body {
    margin: 0;
  }

  .empty-state__title {
    color: var(--color-text);
    font-size: var(--text-base);
    font-weight: 700;
  }

  .empty-state__body {
    max-width: 36ch;
    font-size: var(--text-sm);
    line-height: 1.45;
  }
</style>
