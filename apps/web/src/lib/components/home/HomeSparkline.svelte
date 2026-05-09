<script lang="ts">
  /**
   * HomeSparkline — ADR-0014.
   *
   * 14-day mood sparkline. Custom SVG (~80 LOC) instead of a charting
   * library because the visual is trivial and the bundle savings are
   * substantial (uPlot 45 KB / Chart.js 175 KB / ApexCharts 400 KB).
   *
   * Theme-aware: the polyline uses `currentColor` so it reads against
   * any palette. Missing days draw nothing on the data layer; instead
   * a dashed line bridges the nearest known points so the eye can
   * still follow the trend.
   *
   * Accessibility:
   *  - The chart itself has `role="img"` plus an `aria-label`.
   *  - Per data point we append a `<title>` so hovering / focusing
   *    surfaces the date + value to AT users.
   */

  import { onMount, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import { buildSparkline, type SparklinePoint } from '$lib/utils/sparkline';
  import { shiftIsoDate } from '$lib/utils/streak';

  /** ISO of the rightmost x-axis date (today). */
  export let todayIso: string;
  /** Pre-loaded entries (any 14-day window covering todayIso back). */
  export let entries: EntryResponse[] = [];
  /** Number of days on the x-axis. ADR-0014 mandates 14. */
  export let days = 14;
  export let height = 32;
  export let min = 1;
  export let max = 5;
  export let loading = false;

  // ResizeObserver keeps the SVG width in sync with the container.
  let container: HTMLDivElement | null = null;
  let measuredWidth = 280;
  let observer: ResizeObserver | null = null;

  onMount(() => {
    if (!container || typeof ResizeObserver === 'undefined') return;
    observer = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r && r.width > 0) measuredWidth = Math.round(r.width);
    });
    observer.observe(container);
  });

  onDestroy(() => {
    observer?.disconnect();
    observer = null;
  });

  // --------------------------------------------------------------
  // Build the 14-day point array (oldest left, today right).
  // --------------------------------------------------------------

  $: points = buildPoints(entries, todayIso, days);
  $: geometry = buildSparkline(points, measuredWidth, height, min, max);

  function buildPoints(list: readonly EntryResponse[], today: string, n: number): SparklinePoint[] {
    const byDate = new Map<string, EntryResponse>();
    for (const e of list) {
      if (e.slot === 'day') byDate.set(e.entry_date, e);
    }
    const out: SparklinePoint[] = [];
    for (let i = n - 1; i >= 0; i -= 1) {
      const iso = shiftIsoDate(today, -i);
      const e = byDate.get(iso);
      out.push({ date: iso, value: e ? e.mood_score : null });
    }
    return out;
  }
</script>

<section
  class="home-sparkline"
  data-testid="home-sparkline"
  aria-label={$_('home.sparkline.heading')}
>
  <header class="home-sparkline__header">
    <h2 class="home-sparkline__heading">{$_('home.sparkline.heading')}</h2>
    <span class="home-sparkline__caption"
      >{$_('home.sparkline.caption', { values: { n: days } })}</span
    >
  </header>

  <div class="home-sparkline__chart" bind:this={container}>
    <svg
      role="img"
      aria-label={$_('home.sparkline.aria_label', { values: { n: days } })}
      viewBox={`0 0 ${geometry.width} ${geometry.height}`}
      preserveAspectRatio="none"
      class="home-sparkline__svg"
      width={geometry.width}
      height={geometry.height}
      data-loading={loading ? 'true' : 'false'}
    >
      {#each geometry.dashedSegments as seg, i (i)}
        <line
          class="home-sparkline__line home-sparkline__line--dashed"
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
          stroke="currentColor"
          stroke-width="1.5"
          stroke-dasharray="3 3"
          opacity="0.6"
        />
      {/each}
      {#each geometry.solidSegments as seg, i (i)}
        <line
          class="home-sparkline__line home-sparkline__line--solid"
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
        />
      {/each}
      {#each geometry.coords as c (c.date)}
        {#if c.y !== null}
          <g class="home-sparkline__point">
            <circle
              cx={c.x}
              cy={c.y}
              r="2.25"
              fill="currentColor"
              stroke="rgb(var(--color-surface-50, 250 250 252))"
              stroke-width="1"
            />
            <title>{c.date} · {c.value ?? ''}</title>
          </g>
        {/if}
      {/each}
    </svg>
  </div>
</section>

<style>
  .home-sparkline {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    color: rgb(var(--color-primary-600, 37 99 235));
  }

  .home-sparkline__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
    color: rgb(var(--color-surface-900, 17 24 39));
  }

  .home-sparkline__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .home-sparkline__caption {
    font-size: 0.7rem;
    opacity: 0.6;
  }

  .home-sparkline__chart {
    width: 100%;
  }

  .home-sparkline__svg {
    width: 100%;
    display: block;
  }

  .home-sparkline__svg[data-loading='true'] {
    opacity: 0.4;
  }
</style>
