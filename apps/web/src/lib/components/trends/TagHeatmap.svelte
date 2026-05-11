<script lang="ts">
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import { heatmapLevel } from '$lib/utils/charts';
  import { shiftIsoDate } from '$lib/utils/streak';

  export let heatmap: TagHeatmapResponse | null = null;
  export let loading = false;

  const skeletonRows = [0, 1, 2, 3];

  let scroller: HTMLDivElement;
  let lastScrolledHeatmap: TagHeatmapResponse | null = null;

  $: dates = heatmap ? buildDates(heatmap.start_date, heatmap.end_date) : [];
  $: maxCount = heatmap
    ? Math.max(0, ...heatmap.tags.flatMap((tag) => tag.days.map((day) => day.count)))
    : 0;
  $: showSkeleton = loading && !heatmap;
  $: if (heatmap && heatmap !== lastScrolledHeatmap) {
    lastScrolledHeatmap = heatmap;
    void scrollToLatest();
  }

  function buildDates(start: string, end: string): string[] {
    const out: string[] = [];
    let cursor = start;
    while (cursor <= end && out.length < 370) {
      out.push(cursor);
      cursor = shiftIsoDate(cursor, 1);
    }
    return out;
  }

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (scroller) {
      scroller.scrollLeft = scroller.scrollWidth;
    }
  }

  function countFor(tagIndex: number, date: string): number {
    const tag = heatmap?.tags[tagIndex];
    if (!tag) return 0;
    return tag.days.find((day) => day.date === date)?.count ?? 0;
  }
</script>

<section class="heatmap" data-loading={loading ? 'true' : 'false'}>
  <div class="heatmap__head">
    <h2>{$_('trends.heatmap.heading')}</h2>
    {#if heatmap}
      <span>{heatmap.start_date} - {heatmap.end_date}</span>
    {/if}
  </div>

  {#if showSkeleton}
    <div class="heatmap__skeleton" role="status" aria-label={$_('trends.heatmap.loading')}>
      {#each skeletonRows as skeletonIndex}
        <span style={`--skeleton-index: ${skeletonIndex}`}></span>
      {/each}
    </div>
  {:else if heatmap && heatmap.tags.length > 0}
    <div class="heatmap__scroller" aria-label={$_('trends.heatmap.aria')} bind:this={scroller}>
      <div class="heatmap__grid" style={`--day-count: ${dates.length}`}>
        {#each heatmap.tags as tag, tagIndex}
          <div class="heatmap__tag" title={tag.name}>{tag.name}</div>
          {#each dates as date}
            {@const count = countFor(tagIndex, date)}
            <a
              class={`heatmap__cell heatmap__cell--${heatmapLevel(count, maxCount)}`}
              href={`/entries/day/${date}?tag_id=${tag.tag_id}`}
              aria-label={`${tag.name}, ${date}: ${count}`}
              title={`${tag.name}, ${date}: ${count}`}
            ></a>
          {/each}
        {/each}
      </div>
    </div>
    <div class="heatmap__legend" aria-label={$_('trends.heatmap.legend')}>
      <span>{$_('trends.heatmap.less')}</span>
      {#each [0, 1, 2, 3, 4] as level}
        <span class={`heatmap__legend-cell heatmap__cell--${level}`}></span>
      {/each}
      <span>{$_('trends.heatmap.more')}</span>
    </div>
  {:else if !loading}
    <div class="heatmap__empty">
      <p>{$_('trends.heatmap.empty')}</p>
      <a class="btn btn-sm variant-soft-primary" href="/entries/new">{$_('trends.empty_cta')}</a>
    </div>
  {/if}
</section>

<style>
  .heatmap {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .heatmap__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .heatmap__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
    font-weight: 650;
  }

  .heatmap__head span {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .heatmap__scroller {
    overflow-x: auto;
    padding-bottom: var(--space-1);
    scroll-behavior: smooth;
  }

  .heatmap__grid {
    display: grid;
    grid-template-columns: minmax(7rem, 9rem) repeat(var(--day-count), 0.8rem);
    gap: 0.18rem;
    min-width: max-content;
    align-items: center;
  }

  .heatmap__tag {
    position: sticky;
    left: 0;
    z-index: 1;
    padding: var(--space-1) var(--space-2) var(--space-1) 0;
    font-size: var(--text-xs);
    background: var(--color-surface-tag-bg);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .heatmap__cell,
  .heatmap__legend-cell {
    width: 0.8rem;
    height: 0.8rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-dynamic);
  }

  .heatmap__cell:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .heatmap__cell--1 {
    background: var(--color-heatmap-1);
  }

  .heatmap__cell--2 {
    background: var(--color-heatmap-2);
  }

  .heatmap__cell--3 {
    background: var(--color-heatmap-3);
  }

  .heatmap__cell--4 {
    background: var(--color-heatmap-4);
  }

  .heatmap__legend,
  .heatmap__empty {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .heatmap__empty {
    justify-content: space-between;
    font-size: var(--text-sm);
  }

  .heatmap__empty p {
    margin: 0;
  }

  .heatmap__skeleton {
    min-height: 10rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    padding: var(--space-4);
    display: grid;
    gap: var(--space-2);
  }

  .heatmap__skeleton span {
    border-radius: var(--radius-sm);
    background: linear-gradient(
      90deg,
      var(--color-surface-dynamic),
      var(--color-primary-highlight),
      var(--color-surface-dynamic)
    );
    background-size: 220% 100%;
    animation: heatmap-shimmer 1.1s ease-in-out infinite;
  }

  .heatmap[data-loading='true'] {
    opacity: 0.92;
  }

  @keyframes heatmap-shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: -100% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .heatmap__scroller {
      scroll-behavior: auto;
    }

    .heatmap__skeleton span {
      animation: none;
    }
  }

  @media (pointer: coarse) {
    .heatmap__grid {
      grid-template-columns: minmax(7rem, 9rem) repeat(var(--day-count), 2.75rem);
      gap: 0.25rem;
    }

    .heatmap__cell {
      width: 2.75rem;
      height: 2.75rem;
    }
  }

  @media (max-width: 520px) {
    .heatmap__head,
    .heatmap__empty {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
