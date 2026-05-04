<script lang="ts">
  /**
   * 1..5 scale slider with explicit +/- buttons (a11y guidance from
   * Issue #7: "Mood-Slider Svelte-Komponente — a11y: +/- Buttons zusätzlich").
   *
   * Renders a native range input plus two icon-buttons so users on
   * touch and keyboard get the same affordance. Labels and aria text
   * are passed in by the caller — this component does not own copy.
   */

  export let value: number;
  export let label: string;
  export let decrementLabel: string;
  export let incrementLabel: string;
  export let id: string;
  export let min = 1;
  export let max = 5;

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
      −
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
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 50%;
    border: 1px solid var(--color-border, #d4d4d4);
    background: transparent;
    font-size: 1.25rem;
    line-height: 1;
    cursor: pointer;
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
</style>
