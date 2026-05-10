<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import { heatmapLevel } from '$lib/utils/charts';
  import { shiftIsoDate } from '$lib/utils/streak';

  export let heatmap: TagHeatmapResponse | null = null;
  export let loading = false;

  $: dates = heatmap ? buildDates(heatmap.start_date, heatmap.end_date) : [];
  $: maxCount = heatmap
    ? Math.max(0, ...heatmap.tags.flatMap((tag) => tag.days.map((day) => day.count)))
    : 0;

  function buildDates(start: string, end: string): string[] {
    const out: string[] = [];
    let cursor = start;
    while (cursor <= end && out.length < 370) {
      out.push(cursor);
      cursor = shiftIsoDate(cursor, 1);
    }
    return out;
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

  {#if heatmap && heatmap.tags.length > 0}
    <div class="heatmap__scroller" aria-label={$_('trends.heatmap.aria')}>
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
  {:else if !loading}
    <p class="heatmap__empty">{$_('trends.heatmap.empty')}</p>
  {/if}
</section>

<style>
  .heatmap {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }

  .heatmap__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
  }

  .heatmap__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
    font-weight: 650;
  }

  .heatmap__head span {
    font-size: 0.78rem;
    opacity: 0.68;
  }

  .heatmap__scroller {
    overflow-x: auto;
    padding-bottom: 0.25rem;
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
    padding: 0.2rem 0.45rem 0.2rem 0;
    font-size: 0.78rem;
    background: rgb(var(--color-surface-50, 249 250 251));
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .heatmap__cell {
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 0.18rem;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.4);
    background: rgb(var(--color-surface-200, 229 231 235) / 0.45);
  }

  .heatmap__cell:focus {
    outline: 2px solid #01696f;
    outline-offset: 1px;
  }

  .heatmap__cell--1 {
    background: #b8e2df;
  }

  .heatmap__cell--2 {
    background: #73c7c1;
  }

  .heatmap__cell--3 {
    background: #2f9b98;
  }

  .heatmap__cell--4 {
    background: #01696f;
  }

  .heatmap__empty {
    margin: 0;
    font-size: 0.9rem;
    opacity: 0.72;
  }

  .heatmap[data-loading='true'] {
    opacity: 0.55;
  }
</style>
