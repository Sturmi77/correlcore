<script context="module" lang="ts">
  export type PanelVariant = 'plain' | 'bordered' | 'elevated' | 'chart' | 'danger';
  export type PanelElement = 'section' | 'article' | 'div' | 'aside';
</script>

<script lang="ts">
  export let as: PanelElement = 'section';
  export let variant: PanelVariant = 'bordered';
  export let className = '';

  $: classes = ['ui-panel', `ui-panel--${variant}`, className].filter(Boolean).join(' ');
</script>

<svelte:element this={as} {...$$restProps} class={classes}>
  <slot />
</svelte:element>

<style>
  .ui-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    color: var(--color-text);
  }

  .ui-panel--plain {
    gap: var(--space-3);
  }

  .ui-panel--bordered,
  .ui-panel--elevated,
  .ui-panel--chart,
  .ui-panel--danger {
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .ui-panel--elevated {
    box-shadow: var(--shadow-sm);
  }

  .ui-panel--chart {
    min-width: 0;
    overflow: hidden;
  }

  .ui-panel--danger {
    border-color: color-mix(in srgb, var(--color-error) 28%, transparent);
    background: color-mix(in srgb, var(--color-error) 8%, var(--color-surface));
  }
</style>
