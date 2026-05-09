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
  const height = 220;
  const padding = 28;

  const metrics: { key: MetricKey; label: string; color: string }[] = [
    { key: 'mood_avg', label: 'trends.metric.mood', color: '#01696f' },
    { key: 'energy_avg', label: 'trends.metric.energy', color: '#10b981' },
    { key: 'stress_avg', label: 'trends.metric.stress', color: '#ef4444' },
  ];

  $: series = metrics.map((metric) => {
    const raw = buildLinePoints(points, metric.key, width - padding * 2, height - padding * 2);
    const shifted = raw.map((point) => ({ ...point, x: point.x + padding, y: point.y + padding }));
    return { ...metric, points: shifted, path: linePath(shifted) };
  });
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
    {#each [1, 2, 3, 4, 5] as tick}
      <line
        x1={padding}
        x2={width - padding}
        y1={height - padding - ((tick - 1) / 4) * (height - padding * 2)}
        y2={height - padding - ((tick - 1) / 4) * (height - padding * 2)}
        class="timeseries__grid"
      />
      <text
        x="8"
        y={height - padding - ((tick - 1) / 4) * (height - padding * 2) + 4}
        class="timeseries__tick"
      >
        {tick}
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
    gap: 0.8rem;
  }

  .timeseries__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
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
    gap: 0.55rem;
    font-size: 0.78rem;
    opacity: 0.78;
  }

  .timeseries__legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .timeseries__dot {
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 999px;
    background: var(--metric-color);
  }

  .timeseries__chart {
    width: 100%;
    min-height: 15rem;
    border-radius: 0.5rem;
    background: rgb(var(--color-surface-50, 249 250 251) / 0.72);
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.45);
  }

  .timeseries__grid {
    stroke: currentColor;
    opacity: 0.1;
    stroke-width: 1;
  }

  .timeseries__tick {
    font-size: 11px;
    fill: currentColor;
    opacity: 0.45;
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
    stroke: rgb(var(--color-surface-50, 249 250 251));
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
    font-size: 0.9rem;
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
