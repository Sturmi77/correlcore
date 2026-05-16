<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity } from '$lib/api/insights';

  export let maturity: InsightMaturity;
  export let entryCount = 0;

  $: phase = maturity.phase;
  $: label = $_(`maturity.badge.${phase}`, {
    values: { n: entryCount },
  });
  $: tooltip = $_(`maturity.badge.${phase}_tooltip`);
  $: isUncertain = phase === 'early_patterns' || phase === 'provisional';
</script>

<span
  class="maturity-badge"
  class:maturity-badge--uncertain={isUncertain}
  data-testid="insight-maturity-badge"
  data-phase={phase}
  title={tooltip}
  aria-label={tooltip}
>
  {#if isUncertain}
    <span aria-hidden="true">!</span>
  {/if}
  <span>{label}</span>
</span>

<style>
  .maturity-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    align-self: flex-start;
    width: fit-content;
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-full);
    background: var(--color-surface-offset);
    color: var(--color-text);
    font-size: var(--text-xs);
    font-weight: 700;
    line-height: 1.3;
  }

  .maturity-badge[data-phase='early_patterns'] {
    border-color: color-mix(in srgb, var(--color-warning) 30%, var(--color-border));
    background: color-mix(in srgb, var(--color-warning) 12%, var(--color-surface));
    color: var(--color-warning);
  }

  .maturity-badge[data-phase='provisional'] {
    border-color: color-mix(in srgb, var(--color-warning) 42%, var(--color-border));
    background: color-mix(in srgb, var(--color-warning) 16%, var(--color-surface));
    color: var(--color-warning);
  }

  .maturity-badge[data-phase='robust'] {
    border-color: color-mix(in srgb, var(--color-success) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-success) 12%, var(--color-surface));
    color: var(--color-success);
  }
</style>
