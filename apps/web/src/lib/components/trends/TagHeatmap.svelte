<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { tick } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import EntryLaunchButton from '$lib/components/entries/EntryLaunchButton.svelte';
  import { buildIsoDateRange, heatmapLevel, type DailyAxisLayout } from '$lib/utils/charts';
  import { habitDailyAxisLayout } from '$lib/utils/trendsDateAxis';

  export let heatmap: TagHeatmapResponse | null = null;
  export let loading = false;
  /** Keep cells compact on touch devices (e.g. habits detail with many days). */
  export let compact = false;
  /** ISO dates with notes — shows a dot above the date column. */
  export let noteDates: readonly string[] = [];
  /**
   * Shared ADR-0035 day-axis contract (same CSS vars as ComparisonHeatmap).
   * When omitted, derives from compact / coarse-pointer via habitDailyAxisLayout.
   */
  export let axisLayout: DailyAxisLayout | null = null;

  const dispatch = createEventDispatcher<{ selectDate: { date: string; tagId: string } }>();

  const skeletonRows = [0, 1, 2, 3];

  let scroller: HTMLDivElement;
  let lastScrolledHeatmap: TagHeatmapResponse | null = null;
  let coarsePointer = false;

  onMount(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    const mq = window.matchMedia('(pointer: coarse)');
    const sync = () => {
      coarsePointer = mq.matches;
    };
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  });

  $: noteDateSet = new Set(noteDates);
  $: dates = heatmap ? buildIsoDateRange(heatmap.start_date, heatmap.end_date) : [];
  $: maxCount = heatmap
    ? Math.max(0, ...heatmap.tags.flatMap((tag) => tag.days.map((day) => day.count)))
    : 0;
  $: resolvedLayout = axisLayout ?? habitDailyAxisLayout({ compact, coarsePointer });
  $: gridStyle = [
    `--day-count: ${dates.length}`,
    `--axis-label-width: ${resolvedLayout.labelWidth}px`,
    `--axis-day-width: ${resolvedLayout.dayWidth}px`,
    `--axis-gap: ${resolvedLayout.dayGap}px`,
  ].join('; ');
  $: showSkeleton = loading && !heatmap;
  $: if (heatmap && heatmap !== lastScrolledHeatmap) {
    lastScrolledHeatmap = heatmap;
    void scrollToLatest();
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

<!--
  `gridStyle` also sits on the section, not only on `.heatmap__grid`. The legend
  is a sibling of the grid, and CSS variables only reach descendants — so its
  swatches resolved `var(--axis-day-width)` to nothing and collapsed to 0x0 (#957).
-->
<section
  class="heatmap"
  class:heatmap--compact={compact}
  style={gridStyle}
  data-loading={loading ? 'true' : 'false'}
>
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
      <div class="heatmap__grid" style={gridStyle} data-testid="tag-heatmap-grid">
        <div class="heatmap__tag heatmap__tag--notes">{$_('trends.heatmap.notes_row')}</div>
        {#each dates as date}
          <span
            class="heatmap__note-dot"
            class:heatmap__note-dot--active={noteDateSet.has(date)}
            aria-hidden={!noteDateSet.has(date)}
            title={noteDateSet.has(date) ? $_('trends.heatmap.note_present') : undefined}
          ></span>
        {/each}
        {#each heatmap.tags as tag, tagIndex}
          <div class="heatmap__tag" title={tag.name}>{tag.name}</div>
          {#each dates as date}
            {@const count = countFor(tagIndex, date)}
            <button
              type="button"
              class={`heatmap__cell heatmap__cell--${heatmapLevel(count, maxCount)}`}
              aria-label={`${tag.name}, ${date}: ${count}`}
              title={`${tag.name}, ${date}: ${count}`}
              on:click={() => dispatch('selectDate', { date, tagId: tag.tag_id })}
            ></button>
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
      <EntryLaunchButton>{$_('trends.empty_cta')}</EntryLaunchButton>
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
    grid-template-columns: var(--axis-label-width) repeat(var(--day-count), var(--axis-day-width));
    column-gap: var(--axis-gap);
    row-gap: var(--heatmap-cell-gap);
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

  .heatmap__tag--notes {
    color: var(--color-text-muted);
    font-weight: 600;
  }

  .heatmap__note-dot {
    width: 0.45rem;
    height: 0.45rem;
    margin: 0 auto;
    border-radius: var(--radius-full);
    background: transparent;
  }

  .heatmap__note-dot--active {
    background: var(--color-primary);
  }

  .heatmap__cell,
  .heatmap__legend-cell {
    width: var(--axis-day-width);
    height: var(--axis-day-width);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-dynamic);
  }

  button.heatmap__cell {
    padding: 0;
    cursor: pointer;
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

  @media (max-width: 480px) {
    .heatmap__head,
    .heatmap__empty {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
