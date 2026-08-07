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
    dailyAxisXForIndex,
    dailyPlotContentWidth,
    type DailyAxisLayout,
    type MetricKey,
  } from '$lib/utils/charts';
  import { displayTimeseriesValue } from '$lib/utils/metrics';
  import { timelineCursor, timelineCursorDate } from '$lib/stores/timelineCursor';
  import { StripCellMapper } from '$lib/charts/adapter';
  import {
    meanBucketMetric,
    formatBucketRangeLabel,
    type AxisBucket,
  } from '$lib/utils/compareAxisZoom';
  import EventMarkerLayer, { type EventMarker } from './EventMarkerLayer.svelte';
  import TimelineCursorOverlay from './TimelineCursorOverlay.svelte';

  export let points: TimeseriesPoint[] = [];
  export let enabled: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
    sleep_quality_avg: true,
  };
  export let loading = false;
  export let axisDates: string[] = [];
  /**
   * Compare-zoom display buckets (#482). When set, each strip cell aggregates
   * its bucket's days via mean-of-logged-days (Option A: encode the bucket
   * mean), matching the Lines path — a single source of truth, no dual axis
   * against the heatmap. Empty when unzoomed / used standalone.
   */
  export let buckets: readonly AxisBucket[] = [];
  export let axisLayout: DailyAxisLayout = compareDailyAxisLayout;
  export let markers: readonly EventMarker[] = [];
  export let enableCursor = true;

  /** Fade cells whose bucket has missing calendar days, signalling lower coverage. */
  const PARTIAL_COVERAGE_OPACITY = 0.55;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    zoomInBucket: { bucket: AxisBucket };
  }>();

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
    {
      key: 'sleep_quality_avg',
      label: 'trends.metric.sleep_quality',
      mapper: new StripCellMapper({ midpoint: 3, range: 4 }),
    },
  ];

  $: visibleMetrics = metrics.filter((m) => enabled[m.key]);
  $: hasData = points.some((point) => point.entry_count > 0);
  $: showSkeleton = loading && points.length === 0;
  $: plotLayout = {
    labelWidth: 0,
    dayWidth: axisLayout.dayWidth,
    dayGap: axisLayout.dayGap,
    rightPadding: axisLayout.rightPadding,
  };
  // One column per bucket when zoomed, else one per day. Cursor keys, geometry
  // and overlays all follow these keys (bucket starts) — mirrors MetricTimeseries.
  $: displayAxisKeys = buckets.length > 0 ? buckets.map((bucket) => bucket.start) : axisDates;
  $: width = dailyPlotContentWidth(displayAxisKeys, plotLayout);
  $: height =
    paddingTop +
    visibleMetrics.length * stripHeight +
    Math.max(0, visibleMetrics.length - 1) * stripGap +
    paddingBottom;

  // Build a lookup so we can render even sparse data.
  $: byDate = new Map(points.map((p) => [p.period_start, p]));

  type Cell = {
    date: string;
    label: string;
    x: number;
    width: number;
    fill: string;
    opacity: number;
    rawValue: number | null;
    displayValue: number | null;
    sign: 'neg' | 'mid' | 'pos';
  };

  /** Mean of a metric's logged (display-space) values across a bucket's days. */
  function bucketDisplayMean(metric: StripMetric, bucket: AxisBucket): number | null {
    return meanBucketMetric((date) => {
      const point = byDate.get(date);
      const raw = point ? point[metric.key] : null;
      return raw === null || raw === undefined ? null : displayTimeseriesValue(metric.key, raw);
    }, bucket);
  }

  function buildRow(metric: StripMetric): Cell[] {
    const cellW = axisLayout.dayWidth;
    return displayAxisKeys.map((key, index) => {
      const bucket = buckets.length > 0 ? buckets[index] : null;
      let display: number | null;
      let raw: number | null;
      let partial = false;
      let label = key;
      if (bucket) {
        display = bucketDisplayMean(metric, bucket);
        raw = null; // aggregate — no single raw value
        partial = bucket.partial || bucket.presentDays < bucket.dayCount;
        label = formatBucketRangeLabel(bucket);
      } else {
        const point = byDate.get(key) ?? null;
        const value = point ? point[metric.key] : null;
        display =
          value === null || value === undefined ? null : displayTimeseriesValue(metric.key, value);
        raw = value ?? null;
      }
      const encoded = metric.mapper.encode(display ?? NaN);
      const cx = dailyAxisXForIndex(index, plotLayout);
      const opacity =
        encoded.opacity > 0 && partial
          ? encoded.opacity * PARTIAL_COVERAGE_OPACITY
          : encoded.opacity;
      return {
        date: key,
        label,
        x: cx - cellW / 2,
        width: cellW,
        fill: encoded.color,
        opacity,
        rawValue: raw,
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

  // Cursor wiring — same contract as MetricTimeseries: publish bucket starts
  // when zoomed so cursor keys stay aligned with the rendered columns.
  $: if (enableCursor && displayAxisKeys.length > 0) {
    timelineCursor.setAxis(displayAxisKeys);
  }

  /** Remap marker dates onto bucket starts when zoomed; EventMarkerLayer dedupes. */
  $: displayMarkers =
    buckets.length === 0
      ? markers
      : markers
          .map((marker) => {
            const start = buckets.find((b) => b.dates.includes(marker.date))?.start;
            if (!start) return null;
            const end = marker.endDate
              ? buckets.find((b) => b.dates.includes(marker.endDate as string))?.start
              : undefined;
            return {
              ...marker,
              date: start,
              ...(end && end !== start ? { endDate: end } : { endDate: undefined }),
            };
          })
          .filter((marker): marker is EventMarker => marker !== null);

  let hostEl: HTMLDivElement | null = null;

  function nearestDateForX(clientX: number): string | null {
    if (!hostEl || displayAxisKeys.length === 0) return null;
    const gutterWidth = axisLayout.labelWidth;
    const plotRect = hostEl.querySelector('.strip__plot')?.getBoundingClientRect();
    const plotLeft = plotRect?.left ?? hostEl.getBoundingClientRect().left + gutterWidth;
    const plotWidth = plotRect?.width ?? hostEl.getBoundingClientRect().width - gutterWidth;
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
    // A multi-day aggregate cell refines one zoom stage (parity with Lines and
    // the heatmap); a single-day cell opens that day. Prevents opening the
    // bucket's first — possibly empty — day for an aggregate. (#482)
    const bucket = buckets.find((b) => b.start === date) ?? null;
    if (bucket && bucket.dates.length > 1) {
      dispatch('zoomInBucket', { bucket });
      return;
    }
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
        if (displayAxisKeys[0]) timelineCursor.focus(displayAxisKeys[0]);
        break;
      case 'End':
        event.preventDefault();
        if (displayAxisKeys[displayAxisKeys.length - 1])
          timelineCursor.focus(displayAxisKeys[displayAxisKeys.length - 1]);
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
      role="slider"
      tabindex={enableCursor ? 0 : -1}
      aria-label={$_('trends.strip.aria')}
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={Math.max(0, displayAxisKeys.length - 1)}
      aria-valuenow={Math.max(0, displayAxisKeys.indexOf($timelineCursorDate ?? ''))}
      aria-valuetext={$timelineCursorDate ?? undefined}
      on:pointermove={handlePointerMove}
      on:pointerleave={handlePointerLeave}
      on:keydown={handleKeydown}
    >
      <div class="strip__chart-shell">
        <div
          class="strip__gutter"
          style={`width: ${axisLayout.labelWidth}px; height: ${height}px`}
          aria-hidden="true"
        >
          {#each rows as row (row.key)}
            <span class="strip__gutter-label" style={`top: ${row.top + stripHeight / 2}px`}>
              {$_(row.label)}
            </span>
          {/each}
        </div>
        <svg
          class="strip__svg strip__plot"
          style={`--strip-chart-width: ${width}px`}
          {width}
          {height}
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMinYMin meet"
          role="img"
          aria-hidden="true"
        >
          {#each rows as row (row.key)}
            <g class="strip__row" data-metric={row.key}>
              <rect
                class="strip__track"
                x={plotLayout.dayGap}
                y={row.top}
                width={width - plotLayout.dayGap - plotLayout.rightPadding}
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
                    ? `${$_(row.label)} — ${cell.label}`
                    : `${$_(row.label)} — ${cell.label}: ${cell.displayValue.toFixed(1)}`}
                />
              {/each}
            </g>
          {/each}

          <EventMarkerLayer
            markers={displayMarkers}
            axisDates={displayAxisKeys}
            axisLayout={plotLayout}
            height={height - paddingBottom}
            top={0}
          />

          {#if enableCursor}
            <TimelineCursorOverlay
              axisDates={displayAxisKeys}
              axisLayout={plotLayout}
              height={height - paddingBottom}
              top={0}
            />
          {/if}
        </svg>
      </div>
    </div>
  {/if}
</figure>

<style>
  .strip {
    margin: 0;
    display: grid;
    gap: var(--space-2);
  }

  .strip__chart-shell {
    display: flex;
    align-items: stretch;
    min-width: max-content;
  }

  .strip__gutter {
    position: sticky;
    left: 0;
    z-index: 2;
    flex-shrink: 0;
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
    border-right: none;
  }

  .strip__gutter-label {
    position: absolute;
    right: var(--space-2);
    transform: translateY(-50%);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-fg);
    text-align: right;
    max-width: calc(100% - var(--space-2));
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .strip__svg {
    display: block;
    width: var(--strip-chart-width);
    max-width: none;
    height: auto;
    border: 1px solid var(--color-border-chart);
    border-left: none;
    background: var(--color-surface-chart-bg);
  }

  /*
   * Sprint 2 (ADR-0035) a11y wrapper. role='slider' lives here, not on
   * the <svg>. Block-level with min-width: max-content so it shares
   * the same horizontal scroll geometry as the heatmap grid.
   */
  .strip__interactive {
    display: block;
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
    transition: opacity var(--transition-fast);
  }

  .strip__cell:hover {
    /* Slight lift, theme-agnostic. */
    filter: brightness(1.06);
  }

  .strip__skeleton {
    height: 120px;
    border-radius: var(--radius-md, 8px);
    background: var(--color-strip-track-bg);
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
