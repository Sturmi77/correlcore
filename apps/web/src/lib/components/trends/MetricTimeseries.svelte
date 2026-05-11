<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { TimeseriesPoint } from '$lib/api/stats';
  import { buildLinePoints, linePath, type MetricKey } from '$lib/utils/charts';

  export let points: TimeseriesPoint[] = [];
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  export let loading = false;

  const width = 720;
  const height = 240;
  const paddingLeft = 40;
  const paddingRight = 16;
  const paddingTop = 16;
  const paddingBottom = 32;
  const innerW = width - paddingLeft - paddingRight;
  const innerH = height - paddingTop - paddingBottom;

  const metrics: { key: MetricKey; label: string; color: string }[] = [
    { key: 'mood_avg', label: 'trends.metric.mood', color: 'var(--color-metric-mood)' },
    { key: 'energy_avg', label: 'trends.metric.energy', color: 'var(--color-metric-energy)' },
    { key: 'stress_avg', label: 'trends.metric.stress', color: 'var(--color-metric-stress)' },
  ];

  $: series = metrics.map((metric) => {
    const raw = buildLinePoints(points, metric.key, innerW, innerH);
    const shifted = raw.map((point) => ({
      ...point,
      x: point.x + paddingLeft,
      y: point.y + paddingTop,
    }));
    return { ...metric, points: shifted, path: linePath(shifted) };
  });

  $: xLabels = (() => {
    if (points.length === 0) return [];
    const indexes = [0, Math.floor((points.length - 1) / 2), points.length - 1];
    return [...new Set(indexes)].map((index) => ({
      x: paddingLeft + (index / Math.max(1, points.length - 1)) * innerW,
      label: points[index].period_start,
    }));
  })();
</script>

<section class="timeseries" data-loading={loading ? 'true' : 'false'}>
  <div class="timeseries__head">
    <h2>{$_('trends.timeseries.heading')}</h2>
    <div class="timeseries__legend" aria-label={$_('trends.timeseries.legend')}>
      {#each metrics as metric}
        <span class="timeseries__legend-item">
          <span class="timeseries__dot" style={`--metric-color: ${metric.color}`}></span>
          {$_(metric.label)}
        </span>
      {/each}
    </div>
  </div>

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

    {#each [1, 2, 3, 4, 5] as tick}
      {@const y = height - paddingBottom - ((tick - 1) / 4) * innerH}
      <line x1={paddingLeft} x2={width - paddingRight} y1={y} y2={y} class="timeseries__grid" />
      <text x="10" y={y + 4} class="timeseries__tick">
        {tick}
      </text>
    {/each}

    {#each xLabels as tick}
      <text x={tick.x} y={height - 9} class="timeseries__tick timeseries__tick--x">
        {tick.label}
      </text>
    {/each}

    {#each series as metric}
      {#if enabled[metric.key] && metric.path}
        <path d={metric.path} class="timeseries__line" style={`--metric-color: ${metric.color}`} />
        {#each metric.points as point}
          <a
            href={`/entries/new?date=${point.label}`}
            aria-label={`${$_(metric.label)}: ${point.value.toFixed(1)} (${point.label})`}
          >
            <circle
              class="timeseries__point"
              style={`--metric-color: ${metric.color}`}
              cx={point.x}
              cy={point.y}
              r="5"
            >
              <title>{$_(metric.label)}: {point.value.toFixed(1)} ({point.label})</title>
            </circle>
          </a>
        {/each}
      {/if}
    {/each}
  </svg>

  {#if !loading && points.every((point) => point.entry_count === 0)}
    <p class="timeseries__empty">{$_('trends.empty')}</p>
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
    opacity: 0.78;
  }

  .timeseries__legend-item {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
  }

  .timeseries__dot {
    width: 0.55rem;
    height: 0.55rem;
    border-radius: var(--radius-full);
    background: var(--metric-color);
  }

  .timeseries__chart {
    width: 100%;
    min-height: 15rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .timeseries__axis {
    stroke: currentColor;
    opacity: 0.3;
    stroke-width: 1;
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
  }

  .timeseries__point {
    fill: var(--metric-color);
    stroke: var(--color-bg);
    stroke-width: 2;
  }

  .timeseries__point:focus,
  a:focus .timeseries__point {
    outline: none;
    stroke: currentColor;
    stroke-width: 3;
  }

  .timeseries__empty {
    margin: 0;
    font-size: var(--text-sm);
    opacity: 0.72;
  }

  .timeseries[data-loading='true'] {
    opacity: 0.55;
  }

  @media (max-width: 520px) {
    .timeseries__head {
      flex-direction: column;
    }

    .timeseries__legend {
      justify-content: flex-start;
    }
  }
</style>
