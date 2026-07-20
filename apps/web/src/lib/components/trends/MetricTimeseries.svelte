<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TimeseriesPoint, TimeseriesRange } from '$lib/api/stats';
  import {
    buildBucketAxisLinePoints,
    buildDailyAxisLinePoints,
    buildLinePoints,
    compareDailyAxisLayout,
    dailyAxisXForIndex,
    dailyPlotContentWidth,
    formatTimeseriesTick,
    linePath,
    metricStyles,
    type DailyAxisLayout,
    type MetricKey,
  } from '$lib/utils/charts';
  import {
    findBucketForDate,
    formatBucketRangeLabel,
    type AxisBucket,
  } from '$lib/utils/compareAxisZoom';
  import { timelineCursor, timelineCursorDate } from '$lib/stores/timelineCursor';
  import EventMarkerLayer, { type EventMarker } from './EventMarkerLayer.svelte';
  import TimelineCursorOverlay from './TimelineCursorOverlay.svelte';
  import EntryLaunchButton from '$lib/components/entries/EntryLaunchButton.svelte';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  export let loading = false;
  export let axisDates: string[] = [];
  /** When set (Compare zoom), columns and cursor keys follow bucket starts. */
  export let buckets: readonly AxisBucket[] = [];
  export let axisLayout: DailyAxisLayout = compareDailyAxisLayout;
  /**
   * Event markers to render on the shared axis (ADR-0035, M3.8 Sprint 1).
   * Only honoured when the chart is aligned to a daily axis.
   */
  export let markers: readonly EventMarker[] = [];
  /** ISO dates with a note — renders a small presence dot on the axis. */
  export let noteDates: readonly string[] = [];
  /**
   * Enables the shared timeline cursor + hover -> store wiring.
   * Sparkline use cases (Home) keep this off.
   */
  export let enableCursor = false;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    zoomInBucket: { bucket: AxisBucket };
  }>();

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

  $: noteDateSet = new Set(noteDates);
  $: hasData = points.some((point) => point.entry_count > 0);
  $: showSkeleton = loading && points.length === 0;
  $: displayAxisKeys = buckets.length > 0 ? buckets.map((bucket) => bucket.start) : axisDates;
  $: aligned = displayAxisKeys.length > 0;
  $: plotLayout = aligned
    ? {
        labelWidth: 0,
        dayWidth: axisLayout.dayWidth,
        dayGap: axisLayout.dayGap,
        rightPadding: axisLayout.rightPadding,
      }
    : axisLayout;
  $: width = aligned ? dailyPlotContentWidth(displayAxisKeys, plotLayout) : 720;
  $: plotStart = aligned ? plotLayout.dayGap : paddingLeft;
  $: plotEnd = aligned
    ? dailyAxisXForIndex(Math.max(0, displayAxisKeys.length - 1), plotLayout)
    : width - paddingRight;
  $: innerW = plotEnd - plotStart;
  $: series = metrics.map((metric) => {
    const raw = aligned
      ? buckets.length > 0
        ? buildBucketAxisLinePoints(points, metric.key, buckets, innerH, plotLayout)
        : buildDailyAxisLinePoints(points, metric.key, axisDates, innerH, plotLayout)
      : buildLinePoints(points, metric.key, innerW, innerH);
    const shifted = raw.map((point) => ({
      ...point,
      x: aligned ? point.x : point.x + paddingLeft,
      y: point.y + paddingTop,
    }));
    return { ...metric, style: metricStyles[metric.key], points: shifted, path: linePath(shifted) };
  });

  $: xLabels = (() => {
    const labels = aligned ? displayAxisKeys : points.map((point) => point.period_start);
    if (labels.length === 0) return [];
    const indexes = [0, Math.floor((labels.length - 1) / 2), labels.length - 1];
    return [...new Set(indexes)].map((index) => ({
      x: aligned
        ? dailyAxisXForIndex(index, plotLayout)
        : paddingLeft + (index / Math.max(1, labels.length - 1)) * innerW,
      label: formatTimeseriesTick(range, labels[index]),
      date: labels[index],
    }));
  })();

  function diamondPoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`;
  }

  function trianglePoints(x: number, y: number, size: number): string {
    return `${x},${y - size} ${x + size},${y + size} ${x - size},${y + size}`;
  }

  // Sprint 1 (ADR-0035): publish the display axis (bucket starts when zoomed).
  $: if (enableCursor && aligned) {
    timelineCursor.setAxis(displayAxisKeys);
  }

  function nearestDateForX(clientX: number, hostEl: Element): string | null {
    if (!aligned || displayAxisKeys.length === 0) return null;
    const rect = hostEl.getBoundingClientRect();
    const gutterWidth = aligned ? axisLayout.labelWidth : 0;
    const plotRect = hostEl.querySelector('.timeseries__plot')?.getBoundingClientRect();
    const plotLeft = plotRect?.left ?? rect.left + gutterWidth;
    const plotWidth = plotRect?.width ?? rect.width - gutterWidth;
    const local = ((clientX - plotLeft) / plotWidth) * width;
    let bestIndex = 0;
    let bestDelta = Infinity;
    for (let i = 0; i < displayAxisKeys.length; i += 1) {
      const x = dailyAxisXForIndex(i, plotLayout);
      const delta = Math.abs(x - local);
      if (delta < bestDelta) {
        bestDelta = delta;
        bestIndex = i;
      }
    }
    return displayAxisKeys[bestIndex] ?? null;
  }

  function handlePointerMove(event: PointerEvent) {
    if (!enableCursor) return;
    const target = event.currentTarget as Element;
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
      timelineCursor.setDate(displayAxisKeys[0] ?? null, 'keyboard');
    } else if (event.key === 'End') {
      event.preventDefault();
      timelineCursor.setDate(displayAxisKeys[displayAxisKeys.length - 1] ?? null, 'keyboard');
    } else if (event.key === 'Escape') {
      timelineCursor.clear();
    }
  }

  function noteOnAxisKey(axisKey: string): boolean {
    if (buckets.length === 0) return noteDateSet.has(axisKey);
    const bucket = buckets.find((item) => item.start === axisKey);
    return bucket ? bucket.dates.some((date) => noteDateSet.has(date)) : noteDateSet.has(axisKey);
  }

  function pointTitle(metricLabelKey: string, value: number, axisKey: string): string {
    const bucket = findBucketForDate(buckets, axisKey);
    const range = bucket ? formatBucketRangeLabel(bucket) : axisKey;
    const base = `${$_(metricLabelKey)}: ${value.toFixed(1)} (${range})`;
    if (bucket && bucket.dates.length > 1) {
      return `${base} · ${$_('trends.compare.zoom.tap_to_enlarge')}`;
    }
    return base;
  }

  function bucketStartForDate(date: string): string | null {
    if (buckets.length === 0) return displayAxisKeys.includes(date) ? date : null;
    return buckets.find((bucket) => bucket.dates.includes(date))?.start ?? null;
  }

  /** Remap marker dates onto display-axis keys when zoomed. */
  $: displayMarkers =
    buckets.length === 0
      ? markers
      : markers
          .map((marker) => {
            const start = bucketStartForDate(marker.date);
            if (!start) return null;
            const end = marker.endDate ? bucketStartForDate(marker.endDate) : undefined;
            return {
              ...marker,
              date: start,
              ...(end && end !== start ? { endDate: end } : { endDate: undefined }),
            };
          })
          .filter((marker): marker is EventMarker => marker !== null);

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
    <!--
      Sprint 1 (ADR-0035) a11y wrapper.

      The SVG underneath is purely presentational (role='img'). The
      interactive contract lives on this <div> instead, because Svelte
      v5's a11y compiler classifies <svg> as non-interactive.

      We use role='slider' rather than role='application' because:
        - 'slider' is in aria-query's interactive-roles list (accepted
          by both eslint-plugin-svelte and the Svelte v5 compiler),
          while 'application' is not on that list and triggers
          a11y_no_noninteractive_tabindex.
        - 'slider' matches the actual interaction model: the cursor
          travels along a date axis under keyboard control with
          aria-valuemin/max/now/text exposed for screen readers.

      getBoundingClientRect() resolves against this wrapper, which
      spans the same box as the SVG, so the pointer math is unchanged.
    -->
    <div
      class="timeseries__interactive"
      class:timeseries__interactive--active={enableCursor && aligned}
      class:timeseries__interactive--split={aligned}
      role="slider"
      tabindex={enableCursor ? 0 : -1}
      aria-label={$_('trends.timeseries.aria')}
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={Math.max(0, displayAxisKeys.length - 1)}
      aria-valuenow={Math.max(0, displayAxisKeys.indexOf($timelineCursorDate ?? ''))}
      aria-valuetext={$timelineCursorDate ?? undefined}
      on:pointermove={handlePointerMove}
      on:pointerleave={handlePointerLeave}
      on:focus={() =>
        enableCursor && timelineCursor.focus(displayAxisKeys[displayAxisKeys.length - 1] ?? null)}
      on:blur={() => enableCursor && timelineCursor.hover(null)}
      on:keydown={handleKeyDown}
    >
      {#if aligned}
        <div class="timeseries__chart-shell">
          <div
            class="timeseries__gutter"
            style={`width: ${axisLayout.labelWidth}px; height: ${height}px`}
            aria-hidden="true"
          >
            <span class="timeseries__gutter-label">{$_('trends.timeseries.score_axis')}</span>
            {#each [1, 2, 3, 4, 5] as tick}
              {@const y = paddingTop + ((5 - tick) / 4) * innerH}
              <span class="timeseries__gutter-tick" style={`top: ${y}px`}>{tick}</span>
            {/each}
          </div>
          <svg
            class="timeseries__chart timeseries__chart--aligned timeseries__chart--plot"
            class:timeseries__chart--interactive={enableCursor && aligned}
            style={`--timeseries-chart-width: ${width}px`}
            {width}
            {height}
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label={$_('trends.timeseries.aria')}
          >
            {#if enableCursor && displayMarkers.length > 0}
              <EventMarkerLayer
                markers={displayMarkers}
                axisDates={displayAxisKeys}
                axisLayout={plotLayout}
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
            {#each [1, 2, 3, 4, 5] as tick}
              {@const y = height - paddingBottom - ((tick - 1) / 4) * innerH}
              <line x1={plotStart} x2={plotEnd} y1={y} y2={y} class="timeseries__grid" />
            {/each}
            {#each xLabels as tick}
              <text x={tick.x} y={height - 10} class="timeseries__tick timeseries__tick--x">
                {tick.label}
              </text>
            {/each}
            {#if aligned}
              {#each displayAxisKeys as date, index (date)}
                {#if noteOnAxisKey(date)}
                  <circle
                    cx={dailyAxisXForIndex(index, plotLayout)}
                    cy={height - paddingBottom + 14}
                    r="3"
                    class="timeseries__note-dot"
                    data-testid={`timeseries-note-dot-${date}`}
                  >
                    <title>{date}</title>
                  </circle>
                {/if}
              {/each}
            {/if}
            {#if enableCursor}
              <TimelineCursorOverlay
                axisDates={displayAxisKeys}
                axisLayout={plotLayout}
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
                  <button
                    type="button"
                    class="timeseries__point-button"
                    aria-label={pointTitle(metric.label, point.value, point.label)}
                    on:click={() => {
                      const bucket = findBucketForDate(buckets, point.label);
                      if (bucket && bucket.dates.length > 1) {
                        dispatch('zoomInBucket', { bucket });
                        return;
                      }
                      dispatch('selectDate', { date: point.label });
                    }}
                  >
                    <circle class="timeseries__hit" cx={point.x} cy={point.y} r="16">
                      <title>{pointTitle(metric.label, point.value, point.label)}</title>
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
                  </button>
                {/each}
              {/if}
            {/each}
          </svg>
        </div>
      {:else}
        <svg
          class="timeseries__chart"
          class:timeseries__chart--interactive={enableCursor && aligned}
          {width}
          {height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={$_('trends.timeseries.aria')}
        >
          {#if enableCursor && aligned && markers.length > 0}
            <EventMarkerLayer {markers} {axisDates} {axisLayout} top={paddingTop} height={innerH} />
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
          <text
            x={plotStart - 8}
            y={paddingTop + 8}
            class="timeseries__axis-label"
            text-anchor="end"
          >
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
            <TimelineCursorOverlay {axisDates} {axisLayout} top={paddingTop} height={innerH} />
          {/if}

          {#each series as metric}
            {#if enabled[metric.key] && metric.path}
              <path
                d={metric.path}
                class="timeseries__line"
                style={`--metric-color: ${metric.style.color}; --metric-dasharray: ${metric.style.dasharray || 'none'}`}
              />
              {#each metric.points as point}
                <button
                  type="button"
                  class="timeseries__point-button"
                  aria-label={`${$_(metric.label)}: ${point.value.toFixed(1)} (${point.label})`}
                  on:click={() => dispatch('selectDate', { date: point.label })}
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
                </button>
              {/each}
            {/if}
          {/each}
        </svg>
      {/if}
    </div>
  {/if}

  {#if !loading && !hasData}
    <div class="timeseries__empty">
      <p>{$_('trends.timeseries.empty')}</p>
      <EntryLaunchButton>{$_('trends.empty_cta')}</EntryLaunchButton>
    </div>
  {/if}
</section>

<style>
  /* token-exempt-block: SVG axis micro-labels use px for chart precision (F-10). */
  .timeseries {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  /*
   * Stick heading + mood/energy/stress legend to the left of the shared
   * horizontal scroller (same idea as .timeseries__gutter). width:max-content
   * keeps the chrome compact so the legend stays in the visible viewport
   * instead of sitting on the far right of a full-width head row.
   */
  .timeseries__head {
    position: sticky;
    left: 0;
    z-index: 3;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
    width: max-content;
    max-width: min(22rem, 92vw);
    padding-block: var(--space-1);
    padding-inline-end: var(--space-4);
    background: var(--color-bg);
    box-shadow: 0.75rem 0 0.75rem -0.35rem var(--color-bg);
  }

  .timeseries__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
    font-weight: 650;
  }

  .timeseries__legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-start;
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

  .timeseries__interactive--split {
    min-width: max-content;
  }

  .timeseries__chart-shell {
    display: flex;
    align-items: stretch;
    min-width: max-content;
  }

  .timeseries__gutter {
    position: sticky;
    left: 0;
    z-index: 2;
    flex-shrink: 0;
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
    border-right: none;
    border-radius: var(--radius-md) 0 0 var(--radius-md);
    isolation: isolate;
  }

  /* token-exempt: SVG axis micro-labels use px for chart precision (F-10). */
  .timeseries__gutter-label {
    position: absolute;
    top: var(--space-2);
    right: var(--space-2);
    left: var(--space-1);
    font-size: 10px;
    color: var(--color-text-muted);
    text-align: right;
    max-width: 90%;
  }

  .timeseries__gutter-tick {
    position: absolute;
    right: var(--space-2);
    transform: translateY(-50%);
    font-size: 11px;
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }

  .timeseries__chart--plot {
    width: var(--timeseries-chart-width);
    max-width: none;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    border-left: none;
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
  }

  /*
   * Sprint 1 (ADR-0035) a11y wrapper. The SVG above is purely
   * presentational; this <div role="slider"> carries keyboard
   * focus and pointer interactions, and provides the bounding box that
   * pointer math reads via getBoundingClientRect().
   */
  .timeseries__interactive {
    display: block;
    outline: none;
    border-radius: var(--radius-md, 8px);
  }

  .timeseries__interactive--active:focus-visible {
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

  .timeseries__note-dot {
    fill: var(--color-primary);
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

  @media (max-width: 480px) {
    .timeseries__empty {
      flex-direction: column;
      align-items: stretch;
    }

    .timeseries__head {
      max-width: min(18rem, 88vw);
    }
  }
</style>
