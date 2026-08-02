<script lang="ts" context="module">
  import type { TimeseriesPoint } from '$lib/api/stats';

  export interface EventWindow {
    /** Onset date of the event (t = 0). */
    onset: string;
    /** Optional human label rendered in the sub-heading. */
    label?: string;
  }

  // Re-exports kept for backwards-compatibility with earlier imports.
  export { isSmallMultiplesUnlocked, SMALL_MULTIPLES_RADIUS } from './smallMultiplesGate';
</script>

<script lang="ts">
  /**
   * EventAlignedSmallMultiplesSheet — M3.8 Sprint 3 (ADR-0035 §6)
   *
   * Secondary sheet opened from an Insight card. Shows the same metric
   * (mood / energy / stress) across multiple event windows aligned at
   * t = 0 = onset, so co-occurring patterns become visually obvious.
   *
   * Hard rules:
   *   - Phase gate (ADR-0021): the sheet is only mounted when the
   *     insight maturity phase is >= 'provisional'. The Insight card
   *     enforces this before dispatching; the helper above is exposed
   *     so callers can guard their button visibility consistently.
   *   - Token-only colour: every fill / stroke goes through the
   *     chart-adapter divergent encoding. No hue is hardcoded.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturityPhase } from '$lib/api/insights';
  import type { MetricKey } from '$lib/utils/charts';
  import { displayTimeseriesValue } from '$lib/utils/metrics';
  import { StripCellMapper } from '$lib/charts/adapter';
  import { isSmallMultiplesUnlocked, SMALL_MULTIPLES_RADIUS } from './smallMultiplesGate';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';

  export let open = false;
  /** Event windows to align — onset becomes t = 0. */
  export let events: readonly EventWindow[] = [];
  /** All timeseries points available to the sheet — already filtered to the user. */
  export let points: readonly TimeseriesPoint[] = [];
  /** Metric to visualise across the small multiples. */
  export let metric: MetricKey = 'mood_avg';
  /** Insight maturity phase — used to enforce the gate at the boundary. */
  export let phase: InsightMaturityPhase | null = null;
  /**
   * #488: for lag insights, onset (t = 0) is the feature; the outcome is
   * expected at t = +lagOffset. Highlights that column. Null for co-occurrence.
   */
  export let lagOffset: number | null = null;

  const dispatch = createEventDispatcher<{ close: void }>();

  const mapper = new StripCellMapper({ midpoint: 3, range: 4 });
  const radius = SMALL_MULTIPLES_RADIUS;
  const cellSize = 22;
  const cellGap = 4;
  const labelWidth = 110;
  const dayCount = radius * 2 + 1; // -7..+7 inclusive

  const metricI18nKey: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
  };

  $: gateOpen = isSmallMultiplesUnlocked(phase);
  $: metricLabel = $_(metricI18nKey[metric] ?? 'trends.metric.mood');
  $: legendGradient = `linear-gradient(to right, ${mapper.encode(1).color}, ${
    mapper.encode(3).color
  }, ${mapper.encode(5).color})`;

  function isoOffset(iso: string, deltaDays: number): string {
    const [y, m, d] = iso.split('-').map(Number);
    const date = new Date(Date.UTC(y, (m ?? 1) - 1, d ?? 1));
    date.setUTCDate(date.getUTCDate() + deltaDays);
    return date.toISOString().slice(0, 10);
  }

  type WindowRow = {
    onset: string;
    label: string;
    cells: {
      date: string;
      offset: number;
      fill: string;
      opacity: number;
      sign: 'neg' | 'mid' | 'pos';
      displayValue: number | null;
    }[];
  };

  function buildWindow(evt: EventWindow): WindowRow {
    const byDate = new Map(points.map((p) => [p.period_start, p]));
    const cells = [];
    for (let offset = -radius; offset <= radius; offset += 1) {
      const date = isoOffset(evt.onset, offset);
      const point = byDate.get(date) ?? null;
      const raw = point ? point[metric] : null;
      const display =
        raw === null || raw === undefined ? null : displayTimeseriesValue(metric, raw);
      const encoded = mapper.encode(display ?? Number.NaN);
      cells.push({
        date,
        offset,
        fill: encoded.color,
        opacity: encoded.opacity,
        sign: encoded.sign,
        displayValue: display,
      });
    }
    return {
      onset: evt.onset,
      label: evt.label ?? evt.onset,
      cells,
    };
  }

  $: rows = events.map(buildWindow);
  $: gridWidth = labelWidth + dayCount * (cellSize + cellGap);
  $: gridHeight = rows.length * (cellSize + cellGap) + 32; // + axis labels
  $: sheetOpen = open && gateOpen;
  // Only highlight a lag column that falls inside the rendered ±radius window.
  $: lagColumn =
    lagOffset != null && lagOffset >= -radius && lagOffset <= radius ? lagOffset : null;
  $: lagBandX = lagColumn != null ? labelWidth + (lagColumn + radius) * (cellSize + cellGap) : 0;
</script>

<BottomSheet
  open={sheetOpen}
  labelledBy="esm-title"
  testId="event-aligned-small-multiples-sheet"
  closeAriaLabel={$_('trends.esm.close_aria')}
  on:close={() => dispatch('close')}
>
  <header class="esm__header">
    <div>
      <p class="esm__eyebrow">{$_('trends.esm.eyebrow')}</p>
      <h2 id="esm-title">{$_('trends.esm.title')}</h2>
      <p class="esm__metric" data-testid="esm-metric-label">
        {$_('trends.esm.metric_label', { values: { metric: metricLabel } })}
      </p>
      <p class="esm__body" data-testid="esm-intro">
        {$_('trends.esm.body', { values: { metric: metricLabel } })}
      </p>
      {#if lagColumn != null}
        <p class="esm__lag-note" data-testid="esm-lag-note">
          {$_('trends.esm.lag_hint', { values: { days: lagColumn } })}
        </p>
      {/if}
    </div>
    <button
      type="button"
      class="esm__close"
      aria-label={$_('trends.esm.close_aria')}
      on:click={() => dispatch('close')}
    >
      ×
    </button>
  </header>

  {#if rows.length === 0}
    <p class="esm__empty">{$_('trends.esm.empty')}</p>
  {:else}
    <p class="esm__axis-caption" data-testid="esm-axis-caption">{$_('trends.esm.axis_caption')}</p>
    <div class="esm__scroll">
      <svg
        class="esm__svg"
        viewBox={`0 0 ${gridWidth} ${gridHeight}`}
        role="img"
        aria-label={$_('trends.esm.aria')}
      >
        {#if lagColumn != null}
          <!-- #488: highlight the expected-outcome column at t = +lag_days. -->
          <rect
            class="esm__lag-band"
            data-testid="esm-lag-band"
            x={lagBandX - cellGap / 2}
            y={0}
            width={cellSize + cellGap}
            height={gridHeight}
            rx="4"
          />
        {/if}
        <!-- Offset axis labels (-7 .. +7) -->
        <g class="esm__axis">
          {#each Array.from({ length: dayCount }) as _v, i}
            {@const offset = i - radius}
            <text
              x={labelWidth + i * (cellSize + cellGap) + cellSize / 2}
              y={14}
              text-anchor="middle"
              class="esm__axis-tick"
              class:esm__axis-tick--lag={offset === lagColumn}
            >
              {offset === 0 ? 'T0' : offset > 0 ? `+${offset}` : `${offset}`}
            </text>
          {/each}
        </g>

        {#each rows as row, rowIndex (row.onset)}
          {@const top = 24 + rowIndex * (cellSize + cellGap)}
          <g class="esm__row" data-onset={row.onset}>
            <text
              x={labelWidth - 8}
              y={top + cellSize / 2}
              text-anchor="end"
              dominant-baseline="middle"
              class="esm__row-label"
            >
              {row.label}
            </text>

            {#each row.cells as cell (cell.offset)}
              <rect
                class="esm__cell"
                class:esm__cell--t0={cell.offset === 0}
                class:esm__cell--lag={cell.offset === lagColumn}
                x={labelWidth + (cell.offset + radius) * (cellSize + cellGap)}
                y={top}
                width={cellSize}
                height={cellSize}
                fill={cell.fill}
                opacity={cell.opacity}
                rx="3"
                data-sign={cell.sign}
                aria-label={cell.displayValue === null
                  ? `${row.label} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: —`
                  : `${row.label} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: ${cell.displayValue.toFixed(1)}`}
              >
                <title>
                  {cell.date}{cell.displayValue !== null
                    ? ` — ${cell.displayValue.toFixed(1)}`
                    : ''}
                </title>
              </rect>
            {/each}
          </g>
        {/each}
      </svg>
    </div>
    <p
      class="esm__legend"
      data-testid="esm-legend"
      aria-label={$_('trends.esm.legend_aria', { values: { metric: metricLabel } })}
    >
      <span>{$_('trends.esm.legend_low')}</span>
      <span class="esm__legend-scale" style={`background: ${legendGradient}`}></span>
      <span>{$_('trends.esm.legend_high')}</span>
    </p>
  {/if}
</BottomSheet>

<style>
  /* All colour tokens — no hardcoded hue. ADR-0035 §10. */

  .esm__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-3);
  }

  .esm__eyebrow {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 var(--space-1);
  }

  .esm__header h2 {
    margin: 0;
    font-size: var(--text-lg);
  }

  .esm__body {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .esm__metric {
    margin: var(--space-1) 0 0;
    color: var(--color-text);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .esm__axis-caption {
    margin: 0 0 var(--space-2);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .esm__legend {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: var(--space-2) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .esm__legend-scale {
    flex: 1;
    height: 0.5rem;
    border-radius: var(--radius-full);
    min-width: 4rem;
  }

  .esm__close {
    background: transparent;
    border: 0;
    font-size: var(--text-xl);
    cursor: pointer;
    color: var(--color-text);
    min-width: 44px;
    min-height: 44px;
  }

  .esm__close:focus-visible {
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }

  .esm__empty {
    color: var(--color-text-muted);
  }

  .esm__scroll {
    overflow-x: auto;
  }

  .esm__svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .esm__axis-tick,
  .esm__row-label {
    fill: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .esm__row-label {
    fill: var(--color-fg);
    font-weight: 600;
  }

  .esm__cell--t0 {
    /* The t=0 column carries a thin halo so the anchor line is obvious. */
    stroke: var(--color-cursor);
    stroke-width: 1.5;
  }

  .esm__lag-note {
    margin: var(--space-1) 0 0;
    color: var(--color-cursor);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  /* #488: the expected-outcome column at t = +lag_days. Token-only (ADR-0035 §10). */
  .esm__lag-band {
    fill: var(--color-cursor-halo);
    opacity: 0.18;
  }

  .esm__axis-tick--lag {
    fill: var(--color-cursor);
    font-weight: 700;
  }

  .esm__cell--lag {
    stroke: var(--color-cursor);
    stroke-width: 1.5;
    stroke-dasharray: 3 2;
  }
</style>
