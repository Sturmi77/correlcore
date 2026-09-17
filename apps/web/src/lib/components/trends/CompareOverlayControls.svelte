<script lang="ts">
  /**
   * CompareOverlayControls — issue #919.
   *
   * The A∩B (#908) and Lag-1 (#910) toggles plus their swatch legend, shared
   * by the Compare panel and the mobile settings sheet so the overlays are
   * reachable under 768px. Gates and persistence stay with the parent; this
   * component owns the gate copy so panel and sheet cannot drift apart.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { MIN_COINCIDENCE_DAYS } from '$lib/utils/coincidenceMarkers';
  import { MIN_LAG1_DAYS } from '$lib/utils/lag1Markers';
  import {
    EMPTY_COMPARE_OVERLAY_AVAILABILITY,
    MIN_OVERLAY_PINS,
    shouldShowOverlayPinHint,
    type CompareOverlayAvailability,
  } from '$lib/utils/compareOverlayAvailability';

  export let coincidenceHighlight = false;
  export let lag1Highlight = false;
  /** Gate state derived from the pinned rows by TrendsComparePanel. */
  export let availability: CompareOverlayAvailability = EMPTY_COMPARE_OVERLAY_AVAILABILITY;
  export let overlayHintDismissed = false;
  /** Test/DOM prefix so the panel and sheet instances stay addressable. */
  export let testIdPrefix = 'trends-compare';

  const dispatch = createEventDispatcher<{
    coincidenceChange: { value: boolean };
    lag1Change: { value: boolean };
    dismissPinHint: void;
  }>();

  $: coincidenceHint =
    availability.pinnedCount < MIN_OVERLAY_PINS
      ? $_('trends.compare.coincidence.need_pins')
      : !availability.coincidence
        ? $_('trends.compare.coincidence.empty', { values: { min: MIN_COINCIDENCE_DAYS } })
        : '';

  $: lag1Hint =
    availability.pinnedCount < MIN_OVERLAY_PINS
      ? $_('trends.compare.lag1.need_pins')
      : !availability.lag1
        ? $_('trends.compare.lag1.empty', { values: { min: MIN_LAG1_DAYS } })
        : '';

  $: showPinHint = shouldShowOverlayPinHint(
    availability,
    coincidenceHighlight,
    overlayHintDismissed
  );
</script>

<div class="overlay-controls">
  <div class="overlay-controls__group" data-testid="{testIdPrefix}-coincidence">
    <label class="overlay-controls__toggle">
      <input
        type="checkbox"
        data-testid="{testIdPrefix}-coincidence-toggle"
        checked={coincidenceHighlight && availability.coincidence}
        disabled={!availability.coincidence}
        aria-label={$_('trends.compare.coincidence.toggle_aria')}
        on:change={(event) => dispatch('coincidenceChange', { value: event.currentTarget.checked })}
      />
      {$_('trends.compare.coincidence.toggle')}
    </label>
    {#if coincidenceHint}
      <p class="overlay-controls__hint" data-testid="{testIdPrefix}-coincidence-empty">
        {coincidenceHint}
      </p>
    {/if}
    <slot name="coincidence-detail" />
  </div>

  <div class="overlay-controls__group" data-testid="{testIdPrefix}-lag1">
    <label class="overlay-controls__toggle">
      <input
        type="checkbox"
        data-testid="{testIdPrefix}-lag1-toggle"
        checked={lag1Highlight && availability.lag1}
        disabled={!availability.lag1}
        aria-label={$_('trends.compare.lag1.toggle_aria')}
        on:change={(event) => dispatch('lag1Change', { value: event.currentTarget.checked })}
      />
      {$_('trends.compare.lag1.toggle')}
    </label>
    {#if lag1Hint}
      <p class="overlay-controls__hint" data-testid="{testIdPrefix}-lag1-empty">
        {lag1Hint}
      </p>
    {/if}
    <slot name="lag1-detail" />
  </div>

  <ul class="overlay-controls__swatches" data-testid="{testIdPrefix}-swatches">
    <li>
      <svg viewBox="0 0 40 16" aria-hidden="true" focusable="false">
        <rect class="overlay-controls__swatch-band" x="0" y="0" width="40" height="16" rx="3" />
      </svg>
      {$_('trends.compare.coincidence.swatch')}
    </li>
    <li>
      <svg viewBox="0 0 40 16" aria-hidden="true" focusable="false">
        <line class="overlay-controls__swatch-line" x1="20" y1="0" x2="20" y2="16" />
      </svg>
      {$_('trends.compare.lag1.swatch')}
    </li>
  </ul>

  {#if showPinHint}
    <p class="overlay-controls__pin-hint" data-testid="{testIdPrefix}-pin-hint">
      <span>
        <strong>{$_('trends.compare.overlay_hint_lead')}</strong>
        {$_('trends.compare.overlay_hint_body')}
      </span>
      <button
        type="button"
        class="overlay-controls__pin-hint-dismiss"
        data-testid="{testIdPrefix}-pin-hint-dismiss"
        aria-label={$_('trends.compare.overlay_hint_dismiss_aria')}
        on:click={() => dispatch('dismissPinHint')}
      >
        ×
      </button>
    </p>
  {/if}
</div>

<style>
  .overlay-controls {
    display: grid;
    gap: var(--space-2);
  }

  .overlay-controls__group {
    display: grid;
    gap: var(--space-1);
  }

  .overlay-controls__toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    min-height: var(--tap-target);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .overlay-controls__hint {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .overlay-controls__swatches {
    display: grid;
    gap: var(--space-1);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .overlay-controls__swatches li {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .overlay-controls__swatches svg {
    width: 40px;
    height: 16px;
    flex: none;
  }

  /* Same tokens the markers use, so the key cannot drift from the chart. */
  .overlay-controls__swatch-band {
    fill: var(--color-event-marker-soft);
  }

  .overlay-controls__swatch-line {
    stroke: var(--color-event-marker);
    stroke-width: 1.5;
    stroke-dasharray: 3 2;
  }

  .overlay-controls__pin-hint {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    margin: 0;
    padding: var(--space-2);
    border: 1px solid var(--color-border-chart, var(--color-border));
    border-radius: var(--radius-md, 8px);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--text-xs);
  }

  .overlay-controls__pin-hint-dismiss {
    margin-left: auto;
    min-width: var(--tap-target);
    min-height: var(--tap-target);
    background: transparent;
    border: 0;
    color: var(--color-text-muted);
    font-size: var(--text-lg);
    cursor: pointer;
  }
</style>
