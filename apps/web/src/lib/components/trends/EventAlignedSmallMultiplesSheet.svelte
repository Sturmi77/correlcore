<script lang="ts" context="module">
  import type { TimeseriesPoint } from '$lib/api/stats';

  export interface EventWindow {
    /** Onset date of the event (t = 0). */
    onset: string;
    /** Optional human label rendered in the sub-heading. */
    label?: string;
  }

  // Re-exports kept for backwards-compatibility with earlier imports.
  export {
    hasEnoughOccurrences,
    isSmallMultiplesUnlocked,
    MIN_SMALL_MULTIPLES_OCCURRENCES,
    SMALL_MULTIPLES_RADIUS,
  } from './smallMultiplesGate';
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
   *   - Occurrence floor (#811): median trajectory (#810) requires
   *     ≥ MIN_SMALL_MULTIPLES_OCCURRENCES collapsed episodes (#809).
   *     Below that, individual rows still render with a need-more hint.
   *   - Token-only colour: every fill / stroke goes through the
   *     chart-adapter divergent encoding. No hue is hardcoded.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturityPhase } from '$lib/api/insights';
  import type { MetricKey } from '$lib/utils/charts';
  import { displayTimeseriesValue } from '$lib/utils/metrics';
  import { buildMedianTrajectory, type MedianTrajectoryCell } from '$lib/utils/medianTrajectory';
  import { buildSplitMedianTrajectories } from '$lib/utils/esmSplitMedian';
  import { StripCellMapper } from '$lib/charts/adapter';
  import {
    hasEnoughOccurrences,
    isSmallMultiplesUnlocked,
    MIN_SMALL_MULTIPLES_OCCURRENCES,
    SMALL_MULTIPLES_RADIUS,
  } from './smallMultiplesGate';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import {
    countWindowsWithPartner,
    isPartnerPresentOnDate,
    type EsmPartner,
    type EsmPartnerCandidate,
  } from '$lib/utils/esmPartner';

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
  /**
   * #909: at most one partner subject overlaid in ±7 cells. Null when no
   * co-occurrence partner is available (honest empty — no glyph).
   */
  export let partner: EsmPartner | null = null;
  /** Presence dates for the active partner (heatmap aggregates). */
  export let partnerPresenceDates: readonly string[] = [];
  /** Ranked override candidates (already clamped by the parent). */
  export let partnerCandidates: readonly EsmPartnerCandidate[] = [];
  /** #918: partner lookup still running — distinct from "no partner exists". */
  export let partnerLoading = false;
  /** #918: presence data could not be loaded, so an empty overlay would lie. */
  export let partnerUnavailable = false;

  const dispatch = createEventDispatcher<{
    close: void;
    partnerChange: { partnerId: string | null };
  }>();

  const mapper = new StripCellMapper({ midpoint: 3, range: 4 });
  const radius = SMALL_MULTIPLES_RADIUS;
  const cellSize = 22;
  const cellGap = 4;
  const labelWidth = 110;
  const dayCount = radius * 2 + 1; // -7..+7 inclusive
  const partnerMark = 6;

  const metricI18nKey: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
    sleep_quality_avg: 'trends.metric.sleep_quality',
  };

  $: gateOpen = isSmallMultiplesUnlocked(phase);
  $: metricLabel = $_(metricI18nKey[metric] ?? 'trends.metric.mood');
  $: legendGradient = `linear-gradient(to right, ${mapper.encode(1).color}, ${
    mapper.encode(3).color
  }, ${mapper.encode(5).color})`;
  $: partnerPresenceSet = new Set(partnerPresenceDates);
  $: showPartnerOverlay = partner !== null;
  $: canChoosePartner = partnerCandidates.length > 0;
  // #918: how many windows the partner actually reaches — a count with a
  // denominator, not a rate (v1c decision in FEATURE_EVENT_INTERACTION_TIMELINE).
  $: partnerCoverage = showPartnerOverlay
    ? countWindowsWithPartner(
        events.map((event) => event.onset),
        partnerPresenceSet,
        radius
      )
    : null;

  function isoOffset(iso: string, deltaDays: number): string {
    const [y, m, d] = iso.split('-').map(Number);
    const date = new Date(Date.UTC(y, (m ?? 1) - 1, d ?? 1));
    date.setUTCDate(date.getUTCDate() + deltaDays);
    return date.toISOString().slice(0, 10);
  }

  type EncodedMedianCell = MedianTrajectoryCell & {
    fill: string;
    opacity: number;
    sign: 'neg' | 'mid' | 'pos';
  };

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
  $: showMedian = hasEnoughOccurrences(rows.length);
  $: showNeedMore = rows.length > 0 && !showMedian;

  function encodeMedianCells(cells: readonly MedianTrajectoryCell[]): EncodedMedianCell[] {
    return cells.map((cell) => {
      const encoded = mapper.encode(cell.median ?? Number.NaN);
      return { ...cell, fill: encoded.color, opacity: encoded.opacity, sign: encoded.sign };
    });
  }

  // #920: with a partner chosen, the single median splits into "with" and
  // "without" so a mixed curve can no longer hide the interaction. Each branch
  // carries its own occurrence floor — a median over two windows would read
  // like a finding.
  $: splitMedians = showPartnerOverlay
    ? buildSplitMedianTrajectories(rows, partnerPresenceSet, radius)
    : null;

  $: medianRows = (() => {
    if (splitMedians && partner) {
      return [
        {
          key: 'with' as const,
          label: $_('trends.esm.split_with', { values: { partner: partner.label } }),
          windows: splitMedians.withPartner.windows,
          cells: splitMedians.withPartner.cells
            ? encodeMedianCells(splitMedians.withPartner.cells)
            : null,
        },
        {
          key: 'without' as const,
          label: $_('trends.esm.split_without', { values: { partner: partner.label } }),
          windows: splitMedians.withoutPartner.windows,
          cells: splitMedians.withoutPartner.cells
            ? encodeMedianCells(splitMedians.withoutPartner.cells)
            : null,
        },
      ];
    }
    if (!showMedian) return [];
    return [
      {
        key: 'all' as const,
        label: $_('trends.esm.median_label'),
        windows: rows.length,
        cells: encodeMedianCells(buildMedianTrajectory(rows, radius)),
      },
    ];
  })();

  $: splitCountsLabel =
    splitMedians && partner
      ? $_('trends.esm.split_counts', {
          values: {
            partner: partner.label,
            withCount: splitMedians.withPartner.windows,
            withoutCount: splitMedians.withoutPartner.windows,
          },
        })
      : '';

  /** Fallback copy when no partner is chosen — the split needs one. */
  $: showSplitHint = !showPartnerOverlay && showMedian;

  $: rowCount = rows.length + medianRows.length;
  $: gridWidth = labelWidth + dayCount * (cellSize + cellGap);
  $: gridHeight = rowCount * (cellSize + cellGap) + 32; // + axis labels
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
      <div class="esm__partner" data-testid="esm-partner">
        {#if partnerLoading}
          <p class="esm__partner-empty" data-testid="esm-partner-loading">
            {$_('trends.esm.partner_loading')}
          </p>
        {:else if partnerUnavailable}
          <p class="esm__partner-empty" data-testid="esm-partner-error">
            {$_('trends.esm.partner_error')}
          </p>
        {:else if canChoosePartner}
          <label class="esm__partner-select">
            <span>{$_('trends.esm.partner_label')}</span>
            <select
              data-testid="esm-partner-select"
              aria-label={$_('trends.esm.partner_aria')}
              value={partner?.id ?? ''}
              on:change={(event) =>
                dispatch('partnerChange', {
                  partnerId: event.currentTarget.value || null,
                })}
            >
              {#each partnerCandidates as candidate (candidate.id)}
                <option value={candidate.id}>{candidate.label}</option>
              {/each}
            </select>
          </label>
          {#if showPartnerOverlay && partner}
            <!-- Count first, disclaimer second: the number is what the user came for. -->
            {#if partnerCoverage}
              <p class="esm__partner-summary" data-testid="esm-partner-summary">
                {$_('trends.esm.partner_summary', {
                  values: {
                    partner: partner.label,
                    hits: partnerCoverage.hits,
                    windows: partnerCoverage.windows,
                  },
                })}
              </p>
            {/if}
            <p class="esm__partner-legend" data-testid="esm-partner-legend">
              {$_('trends.esm.partner_legend', { values: { partner: partner.label } })}
            </p>
          {/if}
        {:else}
          <p class="esm__partner-empty" data-testid="esm-partner-empty">
            {$_('trends.esm.partner_empty')}
          </p>
        {/if}
      </div>
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
    {#if showNeedMore}
      <p class="esm__need-more" data-testid="esm-need-more">
        {$_('trends.esm.need_more', { values: { min: MIN_SMALL_MULTIPLES_OCCURRENCES } })}
      </p>
    {/if}
    {#if splitCountsLabel}
      <p class="esm__split-counts" data-testid="esm-split-counts">{splitCountsLabel}</p>
    {:else if showMedian}
      <p class="esm__median-hint" data-testid="esm-median-hint">{$_('trends.esm.median_hint')}</p>
    {/if}
    {#if showSplitHint}
      <p class="esm__median-hint" data-testid="esm-split-hint">{$_('trends.esm.split_hint')}</p>
    {/if}
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

        {#each medianRows as medianRow, medianIndex (medianRow.key)}
          {@const medianTop = 24 + medianIndex * (cellSize + cellGap)}
          {@const medianLabel = medianRow.label}
          <g
            class="esm__row esm__row--median"
            data-testid="esm-median-row"
            data-branch={medianRow.key}
            role="group"
            aria-label={medianRow.key === 'all'
              ? $_('trends.esm.median_aria', { values: { count: medianRow.windows } })
              : $_('trends.esm.split_aria', {
                  values: { branch: medianLabel, count: medianRow.windows },
                })}
          >
            <text
              x={labelWidth - 8}
              y={medianTop + cellSize / 2}
              text-anchor="end"
              dominant-baseline="middle"
              class="esm__row-label esm__row-label--median"
            >
              {medianLabel}
            </text>

            {#if medianRow.cells === null}
              <!-- #920: below the per-branch floor. An honest gap, not a curve. -->
              <rect
                class="esm__split-gap"
                data-testid="esm-split-insufficient"
                x={labelWidth}
                y={medianTop}
                width={dayCount * (cellSize + cellGap) - cellGap}
                height={cellSize}
                rx="3"
              />
              <text
                x={labelWidth + (dayCount * (cellSize + cellGap) - cellGap) / 2}
                y={medianTop + cellSize / 2}
                text-anchor="middle"
                dominant-baseline="middle"
                class="esm__split-gap-label"
              >
                {$_('trends.esm.split_insufficient', { values: { count: medianRow.windows } })}
              </text>
            {/if}

            {#each medianRow.cells ?? [] as cell (cell.offset)}
              <!-- IQR band behind the median cell (token fill, low opacity). -->
              {#if cell.q1 != null && cell.q3 != null && cell.q1 !== cell.q3}
                {@const q1Enc = mapper.encode(cell.q1)}
                {@const q3Enc = mapper.encode(cell.q3)}
                <rect
                  class="esm__iqr"
                  x={labelWidth + (cell.offset + radius) * (cellSize + cellGap) - 1}
                  y={medianTop - 2}
                  width={cellSize + 2}
                  height={cellSize + 4}
                  fill={q1Enc.color}
                  opacity={0.12}
                  rx="4"
                />
                <rect
                  class="esm__iqr"
                  x={labelWidth + (cell.offset + radius) * (cellSize + cellGap) - 1}
                  y={medianTop - 2}
                  width={cellSize + 2}
                  height={cellSize + 4}
                  fill={q3Enc.color}
                  opacity={0.08}
                  rx="4"
                />
              {/if}
              <rect
                class="esm__cell esm__cell--median"
                class:esm__cell--t0={cell.offset === 0}
                class:esm__cell--lag={cell.offset === lagColumn}
                class:esm__cell--median-without={medianRow.key === 'without'}
                x={labelWidth + (cell.offset + radius) * (cellSize + cellGap)}
                y={medianTop}
                width={cellSize}
                height={cellSize}
                fill={cell.fill}
                opacity={cell.opacity}
                rx="3"
                data-sign={cell.sign}
                aria-label={cell.median === null
                  ? `${medianLabel} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: —`
                  : `${medianLabel} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: ${cell.median.toFixed(1)}${
                      cell.q1 != null && cell.q3 != null
                        ? ` (IQR ${cell.q1.toFixed(1)}–${cell.q3.toFixed(1)})`
                        : ''
                    }`}
              >
                <title>
                  {cell.median !== null
                    ? `median ${cell.median.toFixed(1)}${
                        cell.q1 != null && cell.q3 != null
                          ? ` · IQR ${cell.q1.toFixed(1)}–${cell.q3.toFixed(1)}`
                          : ''
                      }`
                    : '—'}
                </title>
              </rect>
            {/each}
          </g>
        {/each}

        {#each rows as row, rowIndex (row.onset)}
          {@const top = 24 + (medianRows.length + rowIndex) * (cellSize + cellGap)}
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
              {@const partnerHit =
                showPartnerOverlay && isPartnerPresentOnDate(cell.date, partnerPresenceSet)}
              {@const cellX = labelWidth + (cell.offset + radius) * (cellSize + cellGap)}
              <rect
                class="esm__cell"
                class:esm__cell--t0={cell.offset === 0}
                class:esm__cell--lag={cell.offset === lagColumn}
                class:esm__cell--partner={partnerHit}
                x={cellX}
                y={top}
                width={cellSize}
                height={cellSize}
                fill={cell.fill}
                opacity={cell.opacity}
                rx="3"
                data-sign={cell.sign}
                data-partner={partnerHit ? 'true' : 'false'}
                aria-label={cell.displayValue === null
                  ? `${row.label} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: —${
                      partnerHit && partner
                        ? ` · ${$_('trends.esm.partner_on_day', { values: { partner: partner.label } })}`
                        : ''
                    }`
                  : `${row.label} ${cell.offset >= 0 ? '+' : ''}${cell.offset}: ${cell.displayValue.toFixed(1)}${
                      partnerHit && partner
                        ? ` · ${$_('trends.esm.partner_on_day', { values: { partner: partner.label } })}`
                        : ''
                    }`}
              >
                <title>
                  {cell.date}{cell.displayValue !== null
                    ? ` — ${cell.displayValue.toFixed(1)}`
                    : ''}{partnerHit && partner
                    ? ` · ${$_('trends.esm.partner_on_day', { values: { partner: partner.label } })}`
                    : ''}
                </title>
              </rect>
              {#if partnerHit}
                <rect
                  class="esm__partner-mark"
                  data-testid="esm-partner-mark"
                  x={cellX + cellSize - partnerMark - 1}
                  y={top + 1}
                  width={partnerMark}
                  height={partnerMark}
                  rx="1"
                >
                  <title
                    >{partner
                      ? $_('trends.esm.partner_on_day', { values: { partner: partner.label } })
                      : ''}</title
                  >
                </rect>
              {/if}
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
      <span>{$_('trends.esm.legend_worse')}</span>
      <span class="esm__legend-scale" style={`background: ${legendGradient}`}></span>
      <span>{$_('trends.esm.legend_better')}</span>
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

  .esm__partner {
    margin-top: var(--space-2);
    display: grid;
    gap: var(--space-1);
  }

  .esm__partner-select {
    display: grid;
    gap: var(--space-1);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text);
  }

  .esm__partner-select select {
    min-height: var(--tap-target);
    max-width: 100%;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }

  .esm__partner-legend,
  .esm__partner-empty {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 400;
  }

  /* #918: the count reads before the disclaimer, so it stays at full contrast. */
  .esm__partner-summary {
    margin: 0;
    color: var(--color-fg);
    font-size: var(--text-xs);
    font-weight: 400;
    font-variant-numeric: tabular-nums;
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

  .esm__need-more,
  .esm__median-hint {
    margin: 0 0 var(--space-2);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .esm__need-more {
    color: var(--color-cursor);
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

  .esm__row-label--median {
    fill: var(--color-cursor);
  }

  .esm__cell--t0 {
    /* The t=0 column carries a thin halo so the anchor line is obvious. */
    stroke: var(--color-cursor);
    stroke-width: 1.5;
  }

  .esm__cell--median {
    stroke: var(--color-cursor);
    stroke-width: 1.5;
  }

  /* #920: the two branches differ by stroke pattern, never by hue (ADR-0035). */
  .esm__cell--median-without {
    stroke-dasharray: 3 2;
  }

  .esm__split-gap {
    fill: none;
    stroke: var(--color-border-chart, var(--color-border));
    stroke-width: 1;
    stroke-dasharray: 4 3;
  }

  .esm__split-gap-label {
    fill: var(--color-text-muted);
    font-size: 10px;
  }

  .esm__split-counts {
    margin: 0 0 var(--space-2);
    color: var(--color-fg);
    font-size: var(--text-sm);
    font-variant-numeric: tabular-nums;
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

  /* #909: partner presence uses esm__partner-mark only — do not override T0/lag strokes. */
  .esm__partner-mark {
    fill: var(--color-event-marker-soft);
    stroke: var(--color-event-marker);
    stroke-width: 1;
    pointer-events: none;
  }
</style>
