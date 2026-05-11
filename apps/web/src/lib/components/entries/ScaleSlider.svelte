<script lang="ts">
  import { _ } from 'svelte-i18n';

  type ScaleType = 'mood' | 'energy' | 'stress' | 'default';

  export let value: number;
  export let label: string;
  export let decrementLabel: string;
  export let incrementLabel: string;
  export let id: string;
  export let min = 1;
  export let max = 5;
  export let scaleType: ScaleType = 'default';

  const scaleLegendKeys: Record<ScaleType, { low: string; high: string }> = {
    mood: { low: 'entry.scale.mood_low', high: 'entry.scale.mood_high' },
    energy: { low: 'entry.scale.energy_low', high: 'entry.scale.energy_high' },
    stress: { low: 'entry.scale.stress_low', high: 'entry.scale.stress_high' },
    default: { low: 'entry.scale.default_low', high: 'entry.scale.default_high' },
  };

  $: legendKeys = scaleLegendKeys[scaleType];
  $: legendLow = $_(legendKeys.low);
  $: legendHigh = $_(legendKeys.high);
  $: legendText = `${min} = ${legendLow}; ${max} = ${legendHigh}`;
  $: legendId = `${id}-legend`;

  function clamp(n: number): number {
    return Math.max(min, Math.min(max, n));
  }

  function decrement() {
    value = clamp(value - 1);
  }

  function increment() {
    value = clamp(value + 1);
  }
</script>

<div class="scale">
  <label class="scale-label" for={id}>{label}</label>
  <div class="scale-row">
    <button
      type="button"
      class="scale-step"
      aria-label={decrementLabel}
      on:click={decrement}
      disabled={value <= min}
    >
      -
    </button>
    <input
      {id}
      type="range"
      {min}
      {max}
      step="1"
      bind:value
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-valuetext={`${value}; ${legendText}`}
      aria-describedby={legendId}
    />
    <button
      type="button"
      class="scale-step"
      aria-label={incrementLabel}
      on:click={increment}
      disabled={value >= max}
    >
      +
    </button>
    <output class="scale-value" for={id}>{value}</output>
  </div>

  <div class="scale-legend" id={legendId}>
    <span class="scale-legend__low">{min} = {legendLow}</span>
    <span class="scale-legend__high">{max} = {legendHigh}</span>
  </div>
</div>

<style>
  .scale {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .scale-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .scale-row {
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    align-items: center;
    gap: var(--space-3);
  }

  .scale-step {
    width: 2.75rem;
    height: 2.75rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border, #d4d4d4);
    background: transparent;
    font-size: 1.25rem;
    line-height: 1;
    cursor: pointer;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive);
  }

  .scale-step:hover:not(:disabled) {
    background: var(--color-surface-dynamic);
    border-color: var(--color-primary);
  }

  .scale-step:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .scale-value {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    min-width: 1.5rem;
    text-align: right;
  }

  input[type='range'] {
    width: 100%;
  }

  .scale-legend {
    display: flex;
    justify-content: space-between;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    padding-inline: 0.125rem;
    padding-inline-start: calc(2.75rem + var(--space-3));
    padding-inline-end: calc(2.75rem + var(--space-3) + 1.5rem + var(--space-3));
  }

  .scale-legend__low,
  .scale-legend__high {
    white-space: nowrap;
  }
</style>
