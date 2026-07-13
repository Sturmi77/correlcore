<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturityPhase } from '$lib/api/insights';
  import type { SymptomTrendPoint } from '$lib/utils/symptomAnalyticsViews';

  export let symptomName: string;
  export let data: SymptomTrendPoint[] = [];
  export let phase: InsightMaturityPhase | null = null;
  export let rollingWindowDays = 7;
  export let showUncertaintyRibbon = true;

  const height = 140;
  const padTop = 12;
  const padBottom = 24;
  const minWidth = 280;
  const maxWidth = 480;

  let chartWidth = 320;
  let chartHost: HTMLElement | null = null;

  $: padLeft = chartWidth < 360 ? 28 : 36;
  $: padRight = chartWidth < 360 ? 28 : 36;
  $: plotWidth = chartWidth - padLeft - padRight;
  $: plotHeight = height - padTop - padBottom;
  $: labelSize = chartWidth < 360 ? 9 : 10;

  $: ribbonEnabled =
    showUncertaintyRibbon && phase !== 'robust' && phase !== null && data.length > 0;

  type Point = { x: number; ySymptom: number; yMood: number | null; point: SymptomTrendPoint };

  $: geometry = buildGeometry(data, plotWidth, padLeft, padTop, plotHeight);

  function buildGeometry(
    points: SymptomTrendPoint[],
    width: number,
    leftPad: number,
    topPad: number,
    height: number
  ): Point[] {
    if (points.length === 0) return [];
    const step = points.length > 1 ? width / (points.length - 1) : 0;
    return points.map((point, index) => ({
      x: leftPad + step * index,
      ySymptom: topPad + (1 - point.symptomFrequency) * height,
      yMood:
        point.moodAverage === null ? null : topPad + (1 - (point.moodAverage - 1) / 4) * height,
      point,
    }));
  }

  function linePath(selector: (p: Point) => number | null): string {
    const segments: string[] = [];
    let open = false;
    for (const point of geometry) {
      const y = selector(point);
      if (y === null) {
        open = false;
        continue;
      }
      segments.push(`${open ? 'L' : 'M'}${point.x.toFixed(1)},${y.toFixed(1)}`);
      open = true;
    }
    return segments.join(' ');
  }

  $: symptomPath = linePath((p) => p.ySymptom);
  $: moodPath = linePath((p) => p.yMood);

  $: ribbonPath = ribbonEnabled ? buildRibbonPath(geometry) : '';

  function buildRibbonPath(points: Point[]): string {
    const upper: string[] = [];
    const lower: string[] = [];
    for (const point of points) {
      if (point.yMood === null || point.point.moodUncertainty === null) continue;
      const delta = (point.point.moodUncertainty / 4) * plotHeight;
      upper.push(`${point.x.toFixed(1)},${(point.yMood - delta).toFixed(1)}`);
      lower.unshift(`${point.x.toFixed(1)},${(point.yMood + delta).toFixed(1)}`);
    }
    if (upper.length === 0) return '';
    return `M${upper.join(' L')} L${lower.join(' L')} Z`;
  }

  onMount(() => {
    const updateWidth = () => {
      const hostWidth = chartHost?.clientWidth ?? minWidth;
      chartWidth = Math.max(minWidth, Math.min(maxWidth, hostWidth));
    };
    updateWidth();
    if (typeof ResizeObserver === 'undefined' || !chartHost) {
      return;
    }
    const observer = new ResizeObserver(updateWidth);
    observer.observe(chartHost);
    return () => observer.disconnect();
  });
</script>

<article class="symptom-trend" aria-labelledby="symptom-trend-heading">
  <header class="symptom-trend__header">
    <h3 id="symptom-trend-heading">{symptomName}</h3>
    <p>
      {$_('insights.symptoms.trend_subtitle', {
        values: { days: data.length, window: rollingWindowDays },
      })}
    </p>
  </header>

  {#if data.length > 0}
    <div class="symptom-trend__chart-host" bind:this={chartHost}>
      <svg
        class="symptom-trend__chart"
        viewBox={`0 0 ${chartWidth} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={$_('insights.symptoms.trend_aria', { values: { name: symptomName } })}
      >
        <line
          x1={padLeft}
          y1={padTop + plotHeight}
          x2={padLeft + plotWidth}
          y2={padTop + plotHeight}
          class="symptom-trend__axis"
        />

        {#if ribbonPath}
          <path d={ribbonPath} class="symptom-trend__ribbon" />
        {/if}

        {#if moodPath}
          <path d={moodPath} class="symptom-trend__line symptom-trend__line--mood" />
        {/if}
        {#if symptomPath}
          <path d={symptomPath} class="symptom-trend__line symptom-trend__line--symptom" />
        {/if}

        <text x={4} y={padTop + 4} class="symptom-trend__ylabel" style={`font-size: ${labelSize}px`}
          >{$_('insights.symptoms.trend_freq')}</text
        >
        <text
          x={chartWidth - 4}
          y={padTop + 4}
          class="symptom-trend__ylabel symptom-trend__ylabel--right"
          style={`font-size: ${labelSize}px`}
        >
          {$_('insights.symptoms.trend_mood')}
        </text>
      </svg>
    </div>

    <ul class="symptom-trend__legend" aria-hidden="true">
      <li>
        <span class="symptom-trend__swatch symptom-trend__swatch--symptom"></span>{symptomName}
      </li>
      <li>
        <span class="symptom-trend__swatch symptom-trend__swatch--mood"></span>{$_(
          'trends.metric.mood'
        )}
      </li>
    </ul>
  {:else}
    <p class="symptom-trend__empty">{$_('insights.symptoms.trend_empty')}</p>
  {/if}
</article>

<style>
  .symptom-trend {
    display: grid;
    gap: var(--space-2);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .symptom-trend__header h3,
  .symptom-trend__header p,
  .symptom-trend__empty {
    margin: 0;
  }

  .symptom-trend__header p,
  .symptom-trend__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-trend__chart-host {
    width: 100%;
    min-width: 0;
  }

  .symptom-trend__chart {
    width: 100%;
    height: auto;
    max-height: 7rem;
    display: block;
  }

  .symptom-trend__axis {
    stroke: var(--color-border-chart);
    stroke-width: 1;
  }

  .symptom-trend__line {
    fill: none;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .symptom-trend__line--symptom {
    stroke: var(--color-warning);
  }

  .symptom-trend__line--mood {
    stroke: var(--color-metric-mood);
  }

  .symptom-trend__ribbon {
    fill: oklch(from var(--color-metric-mood) l c h / 0.18);
    stroke: none;
  }

  .symptom-trend__ylabel {
    fill: var(--color-text-muted);
    font-size: 10px;
  }

  .symptom-trend__ylabel--right {
    text-anchor: end;
  }

  .symptom-trend__legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .symptom-trend__legend li {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
  }

  .symptom-trend__swatch {
    width: 0.75rem;
    height: 0.2rem;
    border-radius: var(--radius-full);
  }

  .symptom-trend__swatch--symptom {
    background: var(--color-warning);
  }

  .symptom-trend__swatch--mood {
    background: var(--color-metric-mood);
  }

  @media (max-width: 480px) {
    .symptom-trend {
      padding: var(--space-2);
      gap: var(--space-1);
    }

    .symptom-trend__chart {
      max-height: 5.25rem;
    }

    .symptom-trend__header p {
      font-size: var(--text-xs);
    }

    .symptom-trend__legend {
      gap: var(--space-2);
    }
  }
</style>
