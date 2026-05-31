<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TimeseriesPoint, TimeseriesRange } from '$lib/api/stats';
  import {
    buildDailyAxisLinePoints,
    buildLinePoints,
    compareDailyAxisLayout,
    dailyAxisChartWidth,
    dailyAxisXForIndex,
    formatTimeseriesTick,
    linePath,
    metricStyles,
    type DailyAxisLayout,
    type MetricKey,
  } from '$lib/utils/charts';
  import { timelineCursor } from '$lib/stores/timelineCursor';
  import EventMarkerLayer, { type EventMarker } from './EventMarkerLayer.svelte';
  import TimelineCursorOverlay from './TimelineCursorOverlay.svelte';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  export let loading = false;
  export let axisDates: string[] = [];
  export let axisLayout: DailyAxisLayout = compareDailyAxisLayout;
  /**
   * Event markers to render on the shared axis (ADR-0035, M3.8 Sprint 1).
   * Only honoured when the chart is aligned to a daily axis.
   */
  export let markers: readonly EventMarker[] = [];
  /**
   * Enables the shared timeline cursor + hover -> store wiring.
   * Sparkline use cases (Home) keep this off.
   */
  export let enableCursor = false;

  const dispatch = createEventDispatcher<{ selectDate: { date: string } }>();

  const height = 248;
  const paddingLeft = 48;
  const paddingRight = 18;
  const paddingTop = 18;
  const paddingBottom = 36;
  const innerH = height - paddingTop - paddingBottom;
  const pointRadius = 5;

  const metrics: { key: MetricKey; label: string }[] = [
    { key: 'mood_avg', label: 'trends.metric.mood' },
    { key: 'energy_avg', label: 'trends.metric.energy' },
    { key: 'stress_avg', label: 'trends.metric.stress' },
  ];

  $: hasData = points.some((point) => point.entry_count > 0);
  $: showSkeleton = loading && points.length === 0;
  $: aligned = axisDates.length > 0;
  $: width = aligned ? dailyAxisChartWidth(axisDates, axisLayout) : 720;
  $: plotStart = aligned ? dailyAxisXForIndex(0, axisLayout) : paddingLeft;
  $: plotEnd = aligned
    ? dailyAxisXForIndex(Math.max(0, axisDates.length - 1), axisLayout)
    : width - paddingRight;
  $: innerW = plotEnd - plotStart;
  $: series = metrics.map((metric) => {
    const raw = aligned
      ? buildDailyAxisLinePoints(points, metric.key, axisDates, innerH, axisLayout)
      : buildLinePoints(points, metric.key, innerW, innerH);
    const shifted = raw.map((point) => ({
      ...point,
      x: aligned ? point.x : point.x + paddingLeft,
      y: point.y + paddingTop,
    }));
    return { ...metric, style: metricStyles[metric.key], points: shifted, path: linePath(shifted) };
  });

  $: xLabels = (() => {
    const labels = aligned ? axisDates : points.map((point) => point.period_start);
    if (labels.length === 0) return [];
    const indexes = [0, Math.floor((labels.length - 1) / 2), labels.length - 1];
    return [...new Set(indexes)].map((index) => ({
      x: aligned
        ? dailyAxisXForIndex(index, axisLayout)
        : paddingLeft + (index / Math.max(1, labels.length - 1)) * innerW,
      label: formatTimeseriesTick(range, labels[index]),
    }));
  })();

  function diamondPoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`;
  }

  function trianglePoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y + size} ${x - size},${y + size}`;
  }

  // Sprint 1 (ADR-0035): publish the canonical axis so other components and
  // keyboard handlers can navigate by date.
  $: if (enableCursor && aligned) {
    timelineCursor.setAxis(axisDates);
  }

  function nearestDateForX(clientX: number, svgEl: SVGSVGElement): string | null {
    if (!aligned || axisDates.length === 0) return null;
    const rect = svgEl.getBoundingClientRect();
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

  function handlePointerMove(event: PointerEvent) {
    if (!enableCursor) return;
    const target = event.currentTarget as SVGSVGElement;
    const date = nearestDateForX(event.clientX, target);
    timelineCursor.hover(date);
  }

  function handlePointerLeave() {
    if (!enableCursor) return;
    timelineCursor.hover(null);
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (!enableCursor) return;
    const step = event.shiftKey ? 7 : 1;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      timelineCursor.move(-step);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      timelineCursor.move(step);
    } else if (event.key === 'Home') {
      event.preventDefault();
      timelineCursor.setDate(axisDates[0] ?? null, 'keyboard');
    } else if (event.key === 'End') {
      event.preventDefault();
      timelineCursor.setDate(axisDates[axisDates.length - 1] ?? null, 'keyboard');
    } else if (event.key === 'Escape') {
      timelineCursor.clear();
    }
  }

  onDestroy(() => {
    // Do not reset the cursor here — other components on the page may still
    // be subscribed. The TrendsComparePanel owns the lifecycle.
  });
</script>

<section class="timeseries" data-loading={loading ? 'true' : 'false'}>
  <div class="timeseries__head">
    <h2>{$_('trends.timeseries.heading')}</h2>
    <div class="timeseries__legend" aria-label={$_('trends.timeseries.legend')}>
      {#each metrics as metric}
        {@const style = metricStyles[metric.key]}
        <span class="timeseries__legend-item">
          <span
            class="timeseries__dot"
            style={`--metric-color: ${style.color}; --metric-dasharray: ${style.dasharray || 'none'}`}
          ></span>
          {$_(metric.label)}
        </span>
      {/each}
    </div>
  </div>

  {#if showSkeleton}
    <div class="timeseries__skeleton" role="status" aria-label={$_('trends.timeseries.loading')}>
      <span></span>
      <span></span>
      <span></span>
    </div>
  {:else}
    <svg
      class="timeseries__chart"
      class:timeseries__chart--aligned={aligned}
      class:timeseries__chart--interactive={enableCursor && aligned}
      style={aligned ? `--timeseries-chart-width: ${width}px` : ''}
      {width}
      {height}
      viewBox={`0 0 ${width} ${height}`}
      role="application"
      tabindex={enableCursor ? 0 : -1}
      aria-label={$_('trends.timeseries.aria')}
      on:pointermove={handlePointerMove}
      on:pointerleave={handlePointerLeave}
      on:focus={() => enableCursor && timelineCursor.focus(axisDates[axisDates.length - 1] ?? null)}
      on:blur={() => enableCursor && timelineCursor.hover(null)}
      on:keydown={handleKeyDown}
    >
      {#if enableCursor && aligned && markers.length > 0}
        <EventMarkerLayer
          {markers}
          {axisDates}
          {axisLayout}
          top={paddingTop}
          height={innerH}
        />
      {/if}
      <line
        x1={plotStart}
        x2={plotStart}
        y1={paddingTop}
        y2={height - paddingBottom}
        class="timeseries__axis"
      />
      <line
        x1={plotStart}
        x2={plotEnd}
        y1={height - paddingBottom}
        y2={height - paddingBottom}
        class="timeseries__axis"
      />
      <text x={plotStart - 8} y={paddingTop + 8} class="timeseries__axis-label" text-anchor="end">
        {$_('trends.timeseries.score_axis')}
      </text>

      {#each [1, 2, 3, 4, 5] as tick}
        {@const y = height - paddingBottom - ((tick - 1) / 4) * innerH}
        <line x1={plotStart} x2={plotEnd} y1={y} y2={y} class="timeseries__grid" />
        <text x={plotStart - 12} y={y + 4} class="timeseries__tick" text-anchor="end">
          {tick}
        </text>
      {/each}

      {#each xLabels as tick}
        <text x={tick.x} y={height - 10} class="timeseries__tick timeseries__tick--x">
          {tick.label}
        </text>
      {/each}

      {#if enableCursor && aligned}
        <TimelineCursorOverlay
          {axisDates}
          {axisLayout}
          top={paddingTop}
          height={innerH}
        />
      {/if}

      {#each series as metric}
        {#if enabled[metric.key] && metric.path}
          <path
            d={metric.path}
            class="timeseries__line"
            style={`--metric-color: ${metric.style.color}; --metric-dasharray: ${metric.style.dasharray || 'none'}`}
          />
          {#each metric.points as point}
            <a
              href={`/entries/day/${point.label}`}
              class="timeseries__point-button"
              aria-label={`${$_(metric.label)}: ${point.value.toFixed(1)} (${point.label})`}
              on:click|preventDefault={() => dispatch('selectDate', { date: point.label })}
            >
              <circle class="timeseries__hit" cx={point.x} cy={point.y} r="16">
                <title>{$_(metric.label)}: {point.value.toFixed(1)} ({point.label})</title>
              </circle>
              {#if metric.style.shape === 'circle'}
                <circle
                  class="timeseries__point"
                  style={`--metric-color: ${metric.style.color}`}
                  cx={point.x}
                  cy={point.y}
                  r={pointRadius}
                />
              {:else if metric.style.shape === 'diamond'}
                <polygon
                  class="timeseries__point"
                  style={`--metric-color: ${metric.style.color}`}
                  points={diamondPoints(point.x, point.y, pointRadius + 1)}
                />
              {:else}
                <polygon
                  class="timeseries__point"
                  style={`--metric-color: ${metric.style.color}`}
                  points={trianglePoints(point.x, point.y, pointRadius + 1)}
                />
              {/if}
            </a>
          {/each}
        {/if}
      {/each}
    </svg>
  {/if}

  {#if !loading && !hasData}
    <div class="timeseries__empty">
      <p>{$_('trends.timeseries.empty')}</p>
      <a class="btn btn-sm variant-soft-primary" href="/entries/new">{$_('trends.empty_cta')}</a>
    </div>
  {/if}
</section>

<style>
  .timeseries {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .timeseries__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .timeseries__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
    font-weight: 650;
  }

  .timeseries__legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--space-2);
    font-size: var(--text-xs);
    opacity: 0.85;
  }

  .timeseries__legend-item {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
  }

  .timeseries__dot {
    width: 1.25rem;
    height: 0;
    border-top: 3px solid var(--metric-color);
    border-radius: var(--radius-full);
    border-style: solid;
    border-image: initial;
    stroke-dasharray: var(--metric-dasharray);
  }

  .timeseries__chart {
    width: 100%;
    min-height: 15.5rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .timeseries__chart--aligned {
    width: var(--timeseries-chart-width);
    max-width: none;
  }

  .timeseries__chart--interactive {
    cursor: crosshair;
    outline: none;
  }

  .timeseries__chart--interactive:focus-visible {
    box-shadow: 0 0 0 2px var(--color-cursor-halo);
  }

  .timeseries__axis {
    stroke: currentColor;
    opacity: 0.34;
    stroke-width: 1;
  }

  .timeseries__axis-label {
    font-size: 10px;
    fill: currentColor;
    opacity: 0.76;
  }

  .timeseries__grid {
    stroke: currentColor;
    opacity: 0.22;
    stroke-width: 1;
    stroke-dasharray: 4 4;
  }

  .timeseries__tick {
    font-size: 11px;
    fill: currentColor;
    opacity: 0.72;
    font-variant-numeric: tabular-nums;
  }

  .timeseries__tick--x {
    font-size: 10px;
    opacity: 0.65;
    text-anchor: middle;
  }

  .timeseries__line {
    fill: none;
    stroke: var(--metric-color);
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: var(--metric-dasharray);
  }

  .timeseries__hit {
    fill: transparent;
    stroke: transparent;
  }

  .timeseries__point {
    fill: var(--metric-color);
    stroke: var(--color-bg);
    stroke-width: 2;
  }

  .timeseries__point-button:focus .timeseries__hit {
    stroke: currentColor;
    stroke-width: 2;
  }

  .timeseries__empty {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    margin: 0;
    font-size: var(--text-sm);
  }

  .timeseries__empty p {
    margin: 0;
    color: var(--color-text-muted);
  }

  .timeseries__skeleton {
    min-height: 15.5rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    padding: var(--space-6);
    display: grid;
    align-content: end;
    gap: var(--space-4);
  }

  .timeseries__skeleton span {
    height: 0.75rem;
    border-radius: var(--radius-full);
    background: linear-gradient(
      90deg,
      var(--color-surface-dynamic),
      var(--color-primary-highlight),
      var(--color-surface-dynamic)
    );
    background-size: 220% 100%;
    animation: timeseries-shimmer 1.1s ease-in-out infinite;
  }

  .timeseries__skeleton span:nth-child(2) {
    width: 78%;
  }

  .timeseries__skeleton span:nth-child(3) {
    width: 56%;
  }

  .timeseries[data-loading='true'] {
    opacity: 0.92;
  }

  @keyframes timeseries-shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: -100% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .timeseries__skeleton span {
      animation: none;
    }
  }

  @media (max-width: 520px) {
    .timeseries__head,
    .timeseries__empty {
      flex-direction: column;
      align-items: stretch;
    }

    .timeseries__legend {
      justify-content: flex-start;
    }
  }
</style>
