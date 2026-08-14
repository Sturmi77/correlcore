<script lang="ts">
  /**
   * Optional 1–5 scale slider (#653 B6).
   *
   * Same look and scale as ScaleSlider (mood/energy/stress) but the value is
   * *optional*: `null` means "not recorded", distinct from a low rating, so an
   * entry never fabricates a default.
   *
   * Two presentations:
   *   - Default (`expandedByDefault = false`): starts collapsed behind an "add
   *     rating" affordance.
   *   - `expandedByDefault = true` (#673): the slider is always visible so the
   *     field is not hidden behind "Optional". While unset it sits at
   *     `defaultValue` with a "not recorded" readout (`–`) and `unsetHint`; the
   *     first interaction records a real value, and the clear control returns
   *     it to `null`.
   *
   * It deliberately does not reuse ScaleSlider via `bind:value`: that component's
   * value is a non-null `number`, so an optional wrapper would fight its type.
   * The markup below mirrors ScaleSlider's so the two look identical when set.
   */
  import { _ } from 'svelte-i18n';

  type ScaleType = 'mood' | 'energy' | 'stress' | 'sleep' | 'default';

  export let value: number | null = null;
  export let label: string;
  export let addLabel: string;
  export let clearLabel: string;
  export let decrementLabel: string;
  export let incrementLabel: string;
  export let id: string;
  export let min = 1;
  export let max = 5;
  /** Value assigned when the user activates the (previously unset) rating. */
  export let defaultValue = 3;
  export let scaleType: ScaleType = 'default';
  export let testId: string | undefined = undefined;
  /** #673: render the slider up front instead of the "add rating" button. */
  export let expandedByDefault = false;
  /** Muted note shown under the slider while unset in expanded mode. */
  export let unsetHint = '';

  $: isUnset = value === null;
  /** Slider position while unset in expanded mode (does not record a value). */
  $: sliderPos = value ?? clamp(defaultValue);
  $: showAddButton = isUnset && !expandedByDefault;

  const scaleLegendKeys: Record<ScaleType, { low: string; high: string }> = {
    mood: { low: 'entry.scale.mood_low', high: 'entry.scale.mood_high' },
    energy: { low: 'entry.scale.energy_low', high: 'entry.scale.energy_high' },
    stress: { low: 'entry.scale.stress_low', high: 'entry.scale.stress_high' },
    sleep: { low: 'entry.scale.sleep_low', high: 'entry.scale.sleep_high' },
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

  function activate(): void {
    value = clamp(defaultValue);
  }

  function clear(): void {
    value = null;
  }

  function decrement(): void {
    // From an unset expanded slider the first step records a value.
    value = clamp(sliderPos - 1);
  }

  function increment(): void {
    value = clamp(sliderPos + 1);
  }

  function onRangeInput(event: Event): void {
    value = clamp(Number((event.currentTarget as HTMLInputElement).value));
  }
</script>

<div class="scale">
  <div class="scale-head">
    <label class="scale-label" for={id}>{label}</label>
    {#if value !== null}
      <button type="button" class="scale-clear" on:click={clear}>{clearLabel}</button>
    {/if}
  </div>

  {#if showAddButton}
    <button
      type="button"
      class="scale-add"
      on:click={activate}
      data-testid={testId}
      aria-describedby={legendId}
    >
      {addLabel}
    </button>
    <div class="scale-legend scale-legend--muted" id={legendId}>
      <span class="scale-legend__low">{min} = {legendLow}</span>
      <span class="scale-legend__high">{max} = {legendHigh}</span>
    </div>
  {:else}
    <div class="scale-row" class:scale-row--unset={isUnset}>
      <button
        type="button"
        class="scale-step"
        aria-label={decrementLabel}
        on:click={decrement}
        disabled={sliderPos <= min}
      >
        -
      </button>
      <input
        {id}
        type="range"
        {min}
        {max}
        step="1"
        value={sliderPos}
        on:input={onRangeInput}
        data-testid={testId}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={sliderPos}
        aria-valuetext={isUnset ? unsetHint || legendText : `${value}; ${legendText}`}
        aria-describedby={legendId}
      />
      <button
        type="button"
        class="scale-step"
        aria-label={incrementLabel}
        on:click={increment}
        disabled={sliderPos >= max}
      >
        +
      </button>
      <output class="scale-value" for={id}>{isUnset ? '–' : value}</output>
    </div>

    {#if isUnset && unsetHint}
      <p class="scale-unset-hint">{unsetHint}</p>
    {/if}

    <div class="scale-legend" id={legendId}>
      <span class="scale-legend__low">{min} = {legendLow}</span>
      <span class="scale-legend__high">{max} = {legendHigh}</span>
    </div>
  {/if}
</div>

<style>
  .scale {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .scale-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .scale-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .scale-clear {
    background: transparent;
    border: none;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    text-decoration: underline;
    cursor: pointer;
    padding: var(--space-1);
    min-height: 2.75rem;
  }

  .scale-add {
    align-self: flex-start;
    min-height: 2.75rem;
    padding: 0 var(--space-4);
    border-radius: var(--radius-full);
    border: 1px dashed var(--color-border);
    background: transparent;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    cursor: pointer;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive);
  }

  .scale-add:hover {
    background: var(--color-surface-dynamic);
    border-color: var(--color-primary);
    color: var(--color-text);
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
    border: 1px solid var(--color-border);
    background: transparent;
    font-size: var(--text-lg);
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

  /* Unset-but-expanded (#673): the slider is visible but not yet recorded. */
  .scale-row--unset .scale-value {
    color: var(--color-text-muted);
    font-weight: 500;
  }

  .scale-unset-hint {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
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

  .scale-legend--muted {
    padding-inline: 0.125rem;
    opacity: 0.7;
  }

  .scale-legend__low,
  .scale-legend__high {
    white-space: nowrap;
  }
</style>
