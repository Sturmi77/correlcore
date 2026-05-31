<script lang="ts">
  /**
   * UnifiedStripChart — M3.8 Sprint 2 (ADR-0035)
   *
   * Divergent strip rendering of mood / energy / stress on the shared
   * compare axis. Replaces the multi-line chart on dense day ranges
   * where overlapping lines hurt readability.
   *
   * Strict rules (ADR-0035):
   *   - All colour comes from theme tokens via the chart adapter
   *     (StripCellMapper / resolveDivergentToken). No hue is hardcoded.
   *   - No chart-library import here. This is the custom-SVG path; the
   *     LayerChart code path lives behind the adapter and is loaded
   *     lazily once the dependency lands (Sprint 2 follow-up).
   *   - The component subscribes to the shared timelineCursor store
   *     and renders TimelineCursorOverlay + EventMarkerLayer on top.
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TimeseriesPoint } from '$lib/api/stats';
  import {
    compareDailyAxisLayout,
    dailyAxisChartWidth,
    dailyAxisXForIndex,
    type DailyAxisLayout,
    type MetricKey,
  } from '$lib/utils/charts';
  import { displayTimeseriesValue } from '$lib/utils/metrics';
  import { timelineCursor, timelineCursorDate } from '$lib/stores/timelineCursor';
  import { StripCellMapper } from '$lib/charts/adapter';
  import EventMarkerLayer, { type EventMarker } from './EventMarkerLayer.svelte';
  import TimelineCursorOverlay from './TimelineCursorOverlay.svelte';

  export let points: TimeseriesPoint[] = [];
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  export let loading = false;
  export let axisDates: string[] = [];
  export let axisLayout: DailyAxisLayout = compareDailyAxisLayout;
  export let markers: readonly EventMarker[] = [];
  export let enableCursor = true;

  const dispatch = createEventDispatcher<{ selectDate: { date: string } }>();

  // Strip geometry — mirrors heatmap row sizing for visual rhyme.
  const stripHeight = 28;
  const stripGap = 10;
  const paddingTop = 12;
  const paddingBottom = 28;

  /**
   * Per-metric divergent mapping configuration.
   *
   * Values enter this component after displayTimeseriesValue(), so stress
   * is already inverted to the same "higher = better" display contract as
   * mood / energy before divergent encoding.
   */
  type StripMetric = {
    key: MetricKey;
    label: string;
    mapper: StripCellMapper;
  };

  const metrics: StripMetric[] = [
    {
      key: 'mood_avg',
      label: 'trends.metric.mood',
      mapper: new StripCellMapper({ midpoint: 3, range: 4 }),
    },
    {
      key: 'energy_avg',
      label: 'trends.metric.energy',
      mapper: new StripCellMapper({ midpoint: 3, range: 4 }),
    },
    {
      key: 'stress_avg',
      label: 'trends.metric.stress',
      mapper: new StripCellMapper({ midpoint: 3, range: 4 }),
    },
  ];

  $: visibleMetrics = metrics.filter((m) => enabled[m.key]);
  $: hasData = points.some((point) => point.entry_count > 0);
  $: showSkeleton = loading && points.length === 0;
  $: width = dailyAxisChartWidth(axisDates, axisLayout);
  $: height =
    paddingTop +
    visibleMetrics.length * stripHeight +
    Math.max(0, visibleMetrics.length - 1) * stripGap +
    paddingBottom;

  // Build a lookup so we can render even sparse data.
  $: byDate = new Map(points.map((p) => [p.period_start, p]));

  type Cell = {
    date: string;
    x: number;
    width: number;
    fill: string;
    opacity: number;
    rawValue: number | null;
    displayValue: number | null;
    sign: 'neg' | 'mid' | 'pos';
  };

  function buildRow(metric: StripMetric): Cell[] {
    return axisDates.map((date, index) => {
      const point = byDate.get(date) ?? null;
      const raw = point ? point[metric.key] : null;
      const display =
        raw === null || raw === undefined ? null : displayTimeseriesValue(metric.key, raw);
      const encoded = metric.mapper.encode(display ?? NaN);
      const cx = dailyAxisXForIndex(index, axisLayout);
      const cellW = axisLayout.dayWidth;
      return {
        date,
        x: cx - cellW / 2,
        width: cellW,
        fill: encoded.color,
        opacity: encoded.opacity,
        rawValue: raw ?? null,
        displayValue: display,
        sign: encoded.sign,
      };
    });
  }

  $: rows = visibleMetrics.map((metric, rowIndex) => {
    const top = paddingTop + rowIndex * (stripHeight + stripGap);
    return {
      ...metric,
      top,
      cells: buildRow(metric),
    };
  });

  // Cursor wiring — same contract as MetricTimeseries.
  $: if (enableCursor && axisDates.length > 0) {
    timelineCursor.setAxis(axisDates);
  }

  let hostEl: HTMLDivElement | null = null;

  function nearestDateForX(clientX: number): string | null {
    if (!hostEl || axisDates.length === 0) return null;
    const rect = hostEl.getBoundingClientRect();
    const local = ((clientX - rect.left) / rect.width) * width;
    let bestIndex = 0;
    let bestDelta = Infinity;
    for (let i = 0; i < axisDates.length; i += 1) {
      const x = dailyAxisXForIndex(i, axisLayout);
      const delta = Math.abs(x - local);
      if (delta < bestDelta) {
        bestDelta = delta;
        bestIndex = i;
      }
    }
    return axisDates[bestIndex] ?? null;
  }

  function handlePointerMove(event: PointerEvent): void {
    if (!enableCursor) return;
    const date = nearestDateForX(event.clientX);
    if (date) timelineCursor.hover(date);
  }

  function handlePointerLeave(): void {
    if (!enableCursor) return;
    timelineCursor.hover(null);
  }

  function handleCellClick(date: string): void {
    if (enableCursor) timelineCursor.focus(date);
    dispatch('selectDate', { date });
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (!enableCursor) return;
    const step = event.shiftKey ? 7 : 1;
    switch (event.key) {
      case 'ArrowLeft':
        event.preventDefault();
        timelineCursor.move(-step);
        break;
      case 'ArrowRight':
        event.preventDefault();
        timelineCursor.move(step);
        break;
      case 'Home':
        event.preventDefault();
        if (axisDates[0]) timelineCursor.focus(axisDates[0]);
        break;
      case 'End':
        event.preventDefault();
        if (axisDates[axisDates.length - 1]) timelineCursor.focus(axisDates[axisDates.length - 1]);
        break;
      case 'Escape':
        event.preventDefault();
        timelineCursor.clear();
        break;
    }
  }
</script>

<figure class="strip" data-testid="unified-strip-chart">
  <figcaption class="visually-hidden">
    {$_('trends.strip.caption')}
  </figcaption>

  {#if showSkeleton}
    <div class="strip__skeleton" aria-hidden="true"></div>
  {:else if !hasData}
    <p class="strip__empty">{$_('trends.empty')}</p>
  {:else}
    <!--
      Sprint 2 (ADR-0035) a11y wrapper. See MetricTimeseries.svelte for
      the full rationale; in short: keyboard + pointer interaction lives
      on this wrapper <div> with role='slider' (an interactive role in
      aria-query's allow-list), never on the underlying <svg> which
      Svelte v5's compiler treats as non-interactive.
    -->
    <div
      class="strip__interactive"
      class:strip__interactive--active={enableCursor}
      bind:this={hostEl}
      style={`--strip-chart-width: ${width}px`}
      role="slider"
      tabindex={enableCursor ? 0 : -1}
      aria-label={$_('trends.strip.aria')}
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={Math.max(0, axisDates.length - 1)}
      aria-valuenow={Math.max(0, axisDates.indexOf($timelineCursorDate ?? ''))}
      aria-valuetext={$timelineCursorDate ?? undefined}
      on:pointermove={handlePointerMove}
      on:pointerleave={handlePointerLeave}
      on:keydown={handleKeydown}
    >
      <svg
        class="strip__svg"
        {width}
        {height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMinYMin meet"
        role="img"
        aria-hidden="true"
      >
        {#each rows as row (row.key)}
          <g class="strip__row" data-metric={row.key}>
            <text
              class="strip__label"
              x={axisLayout.labelWidth - 8}
              y={row.top + stripHeight / 2}
              text-anchor="end"
              dominant-baseline="middle"
            >
              {$_(row.label)}
            </text>
            <rect
              class="strip__track"
              x={axisLayout.labelWidth + axisLayout.dayGap}
              y={row.top}
              width={width - axisLayout.labelWidth - axisLayout.dayGap - axisLayout.rightPadding}
              height={stripHeight}
              rx="4"
            />
            {#each row.cells as cell (cell.date)}
              <rect
                class="strip__cell"
                data-date={cell.date}
                data-sign={cell.sign}
                x={cell.x}
                y={row.top}
                width={cell.width}
                height={stripHeight}
                fill={cell.fill}
                opacity={cell.opacity}
                on:click={() => handleCellClick(cell.date)}
                on:keydown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    handleCellClick(cell.date);
                  }
                }}
                role="button"
                tabindex="-1"
                aria-label={cell.displayValue === null
                  ? `${$_(row.label)} — ${cell.date}`
                  : `${$_(row.label)} — ${cell.date}: ${cell.displayValue.toFixed(1)}`}
              />
            {/each}
          </g>
        {/each}

        <EventMarkerLayer
          {markers}
          {axisDates}
          {axisLayout}
          height={height - paddingBottom}
          top={0}
        />

        {#if enableCursor}
          <TimelineCursorOverlay {axisDates} {axisLayout} height={height - paddingBottom} top={0} />
        {/if}
      </svg>
    </div>
  {/if}
</figure>

<style>
  .strip {
    margin: 0;
    display: grid;
    gap: var(--space-2);
  }

  .strip__svg {
    display: block;
    width: var(--strip-chart-width);
    max-width: none;
    height: auto;
  }

  /*
   * Sprint 2 (ADR-0035) a11y wrapper. role='slider' lives here, not on
   * the <svg>. Block-level with min-width: max-content so it shares
   * the same horizontal scroll geometry as the heatmap grid.
   */
  .strip__interactive {
    display: block;
    width: var(--strip-chart-width);
    min-width: max-content;
    outline: none;
    border-radius: var(--radius-md, 8px);
  }

  .strip__interactive--active:focus-visible {
    box-shadow: 0 0 0 2px var(--color-cursor-halo);
  }

  .strip__track {
    fill: var(--color-strip-track-bg);
  }

  .strip__cell {
    cursor: pointer;
    transition: opacity 120ms ease;
  }

  .strip__cell:hover {
    /* Slight lift, theme-agnostic. */
    filter: brightness(1.06);
  }

  .strip__label {
    fill: var(--color-fg);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .strip__skeleton {
    height: 120px;
    border-radius: var(--radius-md, 8px);
    background: var(--color-surface-muted, var(--color-strip-track-bg));
    animation: strip-pulse 1.4s ease-in-out infinite;
  }

  .strip__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    margin: 0;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  @keyframes strip-pulse {
    0%,
    100% {
      opacity: 0.55;
    }
    50% {
      opacity: 0.95;
    }
  }
</style>
