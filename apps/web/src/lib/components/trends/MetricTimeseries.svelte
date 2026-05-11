<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { TimeseriesPoint, TimeseriesRange } from '$lib/api/stats';
  import {
    buildLinePoints,
    formatTimeseriesTick,
    linePath,
    metricStyles,
    type MetricKey,
  } from '$lib/utils/charts';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  export let loading = false;

  const width = 720;
  const height = 248;
  const paddingLeft = 48;
  const paddingRight = 18;
  const paddingTop = 18;
  const paddingBottom = 36;
  const innerW = width - paddingLeft - paddingRight;
  const innerH = height - paddingTop - paddingBottom;
  const pointRadius = 5;

  const metrics: { key: MetricKey; label: string }[] = [
    { key: 'mood_avg', label: 'trends.metric.mood' },
    { key: 'energy_avg', label: 'trends.metric.energy' },
    { key: 'stress_avg', label: 'trends.metric.stress' },
  ];

  $: hasData = points.some((point) => point.entry_count > 0);
  $: showSkeleton = loading && points.length === 0;
  $: series = metrics.map((metric) => {
    const raw = buildLinePoints(points, metric.key, innerW, innerH);
    const shifted = raw.map((point) => ({
      ...point,
      x: point.x + paddingLeft,
      y: point.y + paddingTop,
    }));
    return { ...metric, style: metricStyles[metric.key], points: shifted, path: linePath(shifted) };
  });

  $: xLabels = (() => {
    if (points.length === 0) return [];
    const indexes = [0, Math.floor((points.length - 1) / 2), points.length - 1];
    return [...new Set(indexes)].map((index) => ({
      x: paddingLeft + (index / Math.max(1, points.length - 1)) * innerW,
      label: formatTimeseriesTick(range, points[index].period_start),
    }));
  })();

  function diamondPoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`;
  }

  function trianglePoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y + size} ${x - size},${y + size}`;
  }
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
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={$_('trends.timeseries.aria')}
    >
      <line
        x1={paddingLeft}
        x2={paddingLeft}
        y1={paddingTop}
        y2={height - paddingBottom}
        class="timeseries__axis"
      />
      <line
        x1={paddingLeft}
        x2={width - paddingRight}
        y1={height - paddingBottom}
        y2={height - paddingBottom}
        class="timeseries__axis"
      />
      <text x={paddingLeft - 8} y={paddingTop + 8} class="timeseries__axis-label" text-anchor="end">
        {$_('trends.timeseries.score_axis')}
      </text>

      {#each [1, 2, 3, 4, 5] as tick}
        {@const y = height - paddingBottom - ((tick - 1) / 4) * innerH}
        <line x1={paddingLeft} x2={width - paddingRight} y1={y} y2={y} class="timeseries__grid" />
        <text x={paddingLeft - 12} y={y + 4} class="timeseries__tick" text-anchor="end">
          {tick}
        </text>
      {/each}

      {#each xLabels as tick}
        <text x={tick.x} y={height - 10} class="timeseries__tick timeseries__tick--x">
          {tick.label}
        </text>
      {/each}

      {#each series as metric}
        {#if enabled[metric.key] && metric.path}
          <path
            d={metric.path}
            class="timeseries__line"
            style={`--metric-color: ${metric.style.color}; --metric-dasharray: ${metric.style.dasharray || 'none'}`}
          />
          {#each metric.points as point}
            <a
              href={`/entries/new?date=${point.label}`}
              aria-label={`${$_(metric.label)}: ${point.value.toFixed(1)} (${point.label})`}
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

  a:focus .timeseries__hit {
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
