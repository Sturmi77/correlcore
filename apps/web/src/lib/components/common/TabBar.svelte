<script context="module" lang="ts">
  export type TabBarOption = {
    id: string;
    label: string;
    disabled?: boolean;
    testId?: string;
  };
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let value: string;
  export let options: TabBarOption[] = [];
  export let ariaLabel: string;
  export let testId: string | undefined = undefined;

  const dispatch = createEventDispatcher<{ change: { value: string } }>();

  function select(nextValue: string): void {
    if (nextValue === value) return;
    dispatch('change', { value: nextValue });
  }
</script>

<div class="tab-bar" role="tablist" aria-label={ariaLabel} data-testid={testId}>
  {#each options as option (option.id)}
    <button
      type="button"
      class="tab-bar__item"
      class:tab-bar__item--active={value === option.id}
      role="tab"
      aria-selected={value === option.id}
      disabled={option.disabled}
      data-testid={option.testId}
      on:click={() => select(option.id)}
    >
      {option.label}
    </button>
  {/each}
</div>

<style>
  .tab-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }

  .tab-bar__item {
    min-width: 44px;
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: var(--radius-full);
    padding: var(--space-2) var(--space-3);
    color: var(--color-text-muted);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    line-height: 1.2;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive),
      color var(--transition-interactive);
  }

  .tab-bar__item--active {
    border-color: color-mix(in srgb, var(--color-primary) 25%, transparent);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
  }

  .tab-bar__item:disabled {
    cursor: not-allowed;
    opacity: 0.54;
  }

  @media (hover: hover) {
    .tab-bar__item:not(:disabled):hover {
      color: var(--color-text);
      background: var(--color-surface-offset);
    }
  }

  @media (max-width: 360px) {
    .tab-bar {
      flex-wrap: nowrap;
      margin-inline: calc(var(--space-2) * -1);
      padding-inline: var(--space-2);
      overflow-x: auto;
      overscroll-behavior-x: contain;
      scrollbar-width: none;
      scroll-padding-inline: var(--space-2);
      -webkit-overflow-scrolling: touch;
    }

    .tab-bar::-webkit-scrollbar {
      display: none;
    }

    .tab-bar__item {
      flex: 0 0 auto;
      padding-inline: var(--space-2);
    }
  }
</style>
