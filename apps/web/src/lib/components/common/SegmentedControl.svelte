<script context="module" lang="ts">
  export type SegmentedControlOption = {
    id: string;
    label: string;
    disabled?: boolean;
    testId?: string;
  };
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let value: string;
  export let options: SegmentedControlOption[] = [];
  export let ariaLabel: string;
  export let testId: string | undefined = undefined;
  export let equalWidth = true;

  const dispatch = createEventDispatcher<{ change: { value: string } }>();

  function select(nextValue: string): void {
    if (nextValue === value) return;
    dispatch('change', { value: nextValue });
  }
</script>

<div
  class="segmented-control"
  class:segmented-control--equal={equalWidth}
  role="group"
  aria-label={ariaLabel}
  data-testid={testId}
>
  {#each options as option (option.id)}
    <button
      type="button"
      class="segmented-control__item"
      class:segmented-control__item--active={value === option.id}
      aria-pressed={value === option.id}
      disabled={option.disabled}
      data-testid={option.testId}
      on:click={() => select(option.id)}
    >
      {option.label}
    </button>
  {/each}
</div>

<style>
  .segmented-control {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    padding: var(--space-1);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .segmented-control--equal .segmented-control__item {
    flex: 1 1 0;
  }

  .segmented-control__item {
    min-width: 44px;
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    padding: 0.45rem 0.7rem;
    background: transparent;
    color: var(--color-text-muted);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    line-height: 1.2;
    text-align: center;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive),
      color var(--transition-interactive);
  }

  .segmented-control__item--active {
    border-color: color-mix(in srgb, var(--color-primary) 26%, transparent);
    background: var(--color-primary);
    color: var(--color-text-inverse);
  }

  .segmented-control__item:disabled {
    cursor: not-allowed;
    opacity: 0.54;
  }

  @media (hover: hover) {
    .segmented-control__item:not(:disabled):hover {
      color: var(--color-text);
      background: var(--color-surface-offset);
    }

    .segmented-control__item--active:not(:disabled):hover {
      color: var(--color-text-inverse);
      background: var(--color-primary);
    }
  }

  @media (max-width: 360px) {
    .segmented-control__item {
      flex-basis: calc(50% - var(--space-1));
    }
  }
</style>
