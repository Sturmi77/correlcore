<script lang="ts">
  /**
   * 1..5 scale slider with explicit +/- buttons (a11y guidance from
   * Issue #7: "Mood-Slider Svelte-Komponente — a11y: +/- Buttons zusätzlich").
   *
   * Renders a native range input plus two icon-buttons so users on
   * touch and keyboard get the same affordance. Labels and aria text
   * are passed in by the caller — this component does not own copy.
   *
   * GAP-01: scaleType prop adds contextual min/max legend so users
   * understand the direction of each metric (esp. stress: 1=relaxed, 5=very stressed).
   */

  export let value: number;
  export let label: string;
  export let decrementLabel: string;
  export let incrementLabel: string;
  export let id: string;
  export let min = 1;
  export let max = 5;

  /**
   * GAP-01: Metrik-Typ — bestimmt die Bedeutungslegende unter dem Slider.
   * mood    → 1 = sehr schlecht … 5 = sehr gut
   * energy  → 1 = erschöpft     … 5 = voller Energie
   * stress  → 1 = entspannt     … 5 = sehr gestresst  (invertierte Valenz!)
   * default → 1 = niedrig       … 5 = hoch
   */
  export let scaleType: 'mood' | 'energy' | 'stress' | 'default' = 'default';

  const scaleLegends: Record<typeof scaleType, { low: string; high: string }> = {
    mood:    { low: 'sehr schlecht', high: 'sehr gut'        },
    energy:  { low: 'erschöpft',    high: 'voller Energie'  },
    stress:  { low: 'entspannt',    high: 'sehr gestresst'  },
    default: { low: 'niedrig',      high: 'hoch'            },
  };

  $: legend = scaleLegends[scaleType];

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

  <!-- GAP-01: Skala-Legende — zeigt Bedeutung von 1 und 5 je Metrik-Typ -->
  <div class="scale-legend" aria-hidden="true">
    <span class="scale-legend__low">{min} = {legend.low}</span>
    <span class="scale-legend__high">{max} = {legend.high}</span>
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

  /* GAP-01: Legende */
  .scale-legend {
    display: flex;
    justify-content: space-between;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    padding-inline: 0.125rem;
    /* Einrücken damit Labels mit den Slider-Endpunkten fluchten */
    padding-inline-start: calc(2.25rem + var(--space-3));
    padding-inline-end: calc(2.25rem + var(--space-3) + 1.5rem + var(--space-3));
  }

  .scale-legend__low,
  .scale-legend__high {
    /* Stress-Wert (high) soll visuell klar als Warnung lesbar sein */
    white-space: nowrap;
  }
</style>
