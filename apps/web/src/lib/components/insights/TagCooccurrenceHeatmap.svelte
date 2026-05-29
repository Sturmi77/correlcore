<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagCooccurrenceRange, TagCooccurrenceResponse } from '$lib/api/insights';
  import {
    buildTagCooccurrenceMatrix,
    cooccurrenceIntensityLevel,
  } from '$lib/utils/tagCooccurrenceMatrix';

  export let data: TagCooccurrenceResponse | null = null;
  export let loading = false;
  export let range: TagCooccurrenceRange = '90d';
  export let minPairsForDisplay = 5;

  const dispatch = createEventDispatcher<{
    rangeChange: { range: TagCooccurrenceRange };
    selectPair: {
      tagAId: string;
      tagBId: string;
      tagAName: string;
      tagBName: string;
      startDate: string;
      endDate: string;
    };
  }>();

  const rangeOptions: TagCooccurrenceRange[] = ['30d', '90d', '1y'];

  $: matrix = data ? buildTagCooccurrenceMatrix(data.pairs) : { tags: [], counts: [] };
  $: maxCount = matrix.counts.flat().reduce((peak, count) => Math.max(peak, count), 0);
  $: hasEnoughPairs = (data?.pairs.length ?? 0) >= minPairsForDisplay;
  $: showSkeleton = loading && !data;

  function rangeLabel(option: TagCooccurrenceRange): string {
    if (option === '30d') return $_('insights.cooccurrence.range_30d');
    if (option === '90d') return $_('insights.cooccurrence.range_90d');
    return $_('insights.cooccurrence.range_1y');
  }
</script>

<section class="cooccurrence" data-loading={loading ? 'true' : 'false'}>
  <div class="cooccurrence__head">
    <div>
      <h2>{$_('insights.cooccurrence.heading')}</h2>
      <p>{$_('insights.cooccurrence.subtitle')}</p>
    </div>
    <div
      class="cooccurrence__range"
      role="group"
      aria-label={$_('insights.cooccurrence.range_label')}
    >
      {#each rangeOptions as option}
        <button
          type="button"
          class:cooccurrence__range--active={range === option}
          aria-pressed={range === option}
          on:click={() => dispatch('rangeChange', { range: option })}
        >
          {rangeLabel(option)}
        </button>
      {/each}
    </div>
  </div>

  {#if showSkeleton}
    <div
      class="cooccurrence__skeleton"
      role="status"
      aria-label={$_('insights.cooccurrence.loading')}
    >
      <span></span>
      <span></span>
      <span></span>
    </div>
  {:else if data && hasEnoughPairs && matrix.tags.length > 0}
    <div class="cooccurrence__scroller" aria-label={$_('insights.cooccurrence.aria')}>
      <div class="cooccurrence__grid" style={`--tag-count: ${matrix.tags.length}`} role="grid">
        <div class="cooccurrence__corner" role="presentation"></div>
        {#each matrix.tags as colTag}
          <div class="cooccurrence__col-label" title={colTag.name}>{colTag.name}</div>
        {/each}

        {#each matrix.tags as rowTag, rowIndex}
          <div class="cooccurrence__row-label" title={rowTag.name}>{rowTag.name}</div>
          {#each matrix.tags as colTag, colIndex}
            {@const count = matrix.counts[rowIndex]?.[colIndex] ?? 0}
            {@const level = cooccurrenceIntensityLevel(count, maxCount)}
            {#if rowIndex === colIndex}
              <div
                class="cooccurrence__cell cooccurrence__cell--empty"
                role="gridcell"
                aria-hidden="true"
              ></div>
            {:else if count > 0}
              <button
                type="button"
                class={`cooccurrence__cell cooccurrence__cell--${level}`}
                role="gridcell"
                aria-label={$_('insights.cooccurrence.cell_aria', {
                  values: { tagA: rowTag.name, tagB: colTag.name, count },
                })}
                title={$_('insights.cooccurrence.cell_title', {
                  values: { tagA: rowTag.name, tagB: colTag.name, count },
                })}
                on:click={() =>
                  dispatch('selectPair', {
                    tagAId: rowTag.tag_id,
                    tagBId: colTag.tag_id,
                    tagAName: rowTag.name,
                    tagBName: colTag.name,
                    startDate: data.start_date,
                    endDate: data.end_date,
                  })}
              >
                <span>{count}</span>
              </button>
            {:else}
              <div
                class="cooccurrence__cell cooccurrence__cell--zero"
                role="gridcell"
                aria-hidden="true"
              ></div>
            {/if}
          {/each}
        {/each}
      </div>
    </div>
    <div class="cooccurrence__legend" aria-label={$_('insights.cooccurrence.legend')}>
      <span>{$_('insights.cooccurrence.less')}</span>
      {#each [1, 2, 3, 4] as level}
        <span class={`cooccurrence__legend-cell cooccurrence__cell--${level}`}></span>
      {/each}
      <span>{$_('insights.cooccurrence.more')}</span>
    </div>
  {:else if !loading}
    <div class="cooccurrence__empty">
      <p>{$_('insights.cooccurrence.empty')}</p>
      <a class="btn btn-sm variant-soft-primary" href="/entries/new">{$_('trends.empty_cta')}</a>
    </div>
  {/if}
</section>

<style>
  .cooccurrence {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
  }

  .cooccurrence__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
    flex-wrap: wrap;
  }

  .cooccurrence__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
    font-weight: 650;
  }

  .cooccurrence__head p {
    margin: var(--space-1) 0 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .cooccurrence__range {
    display: flex;
    gap: var(--space-1);
    padding: var(--space-1);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .cooccurrence__range button {
    min-height: 44px;
    padding: 0 var(--space-3);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-text-muted);
  }

  .cooccurrence__range--active {
    background: var(--color-primary-highlight);
    color: var(--color-primary) !important;
  }

  .cooccurrence__scroller {
    overflow: auto;
    max-width: 100%;
  }

  .cooccurrence__grid {
    display: grid;
    grid-template-columns: minmax(6rem, 8rem) repeat(var(--tag-count), minmax(2.75rem, 1fr));
    gap: 0.2rem;
    min-width: max-content;
    align-items: stretch;
  }

  .cooccurrence__corner {
    position: sticky;
    left: 0;
    z-index: 2;
    background: var(--color-surface-chart-bg);
  }

  .cooccurrence__col-label,
  .cooccurrence__row-label {
    font-size: var(--text-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--color-text-muted);
  }

  .cooccurrence__col-label {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    text-align: left;
    padding: var(--space-1) 0;
    max-height: 6rem;
  }

  .cooccurrence__row-label {
    position: sticky;
    left: 0;
    z-index: 1;
    display: flex;
    align-items: center;
    padding-right: var(--space-2);
    background: var(--color-surface-chart-bg);
  }

  .cooccurrence__cell {
    min-width: 2.75rem;
    min-height: 2.75rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-dynamic);
  }

  .cooccurrence__cell--zero,
  .cooccurrence__cell--empty {
    opacity: 0.35;
  }

  .cooccurrence__cell--1 {
    background: color-mix(in srgb, var(--color-primary) 22%, var(--color-surface-dynamic));
  }

  .cooccurrence__cell--2 {
    background: color-mix(in srgb, var(--color-primary) 40%, var(--color-surface-dynamic));
  }

  .cooccurrence__cell--3 {
    background: color-mix(in srgb, var(--color-primary) 62%, var(--color-surface-dynamic));
  }

  .cooccurrence__cell--4 {
    background: color-mix(in srgb, var(--color-primary) 82%, var(--color-surface-dynamic));
  }

  button.cooccurrence__cell {
    cursor: pointer;
    color: var(--color-text);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  button.cooccurrence__cell:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .cooccurrence__legend,
  .cooccurrence__empty {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .cooccurrence__legend-cell {
    width: 0.9rem;
    height: 0.9rem;
  }

  .cooccurrence__empty {
    justify-content: space-between;
    font-size: var(--text-sm);
  }

  .cooccurrence__empty p {
    margin: 0;
  }

  .cooccurrence__skeleton {
    min-height: 8rem;
    display: grid;
    gap: var(--space-2);
  }

  .cooccurrence__skeleton span {
    border-radius: var(--radius-sm);
    min-height: 1.5rem;
    background: linear-gradient(
      90deg,
      var(--color-surface-dynamic),
      var(--color-primary-highlight),
      var(--color-surface-dynamic)
    );
    background-size: 220% 100%;
    animation: cooccurrence-shimmer 1.1s ease-in-out infinite;
  }

  .cooccurrence[data-loading='true'] {
    opacity: 0.92;
  }

  @keyframes cooccurrence-shimmer {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: -100% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .cooccurrence__skeleton span {
      animation: none;
    }
  }

  @media (max-width: 520px) {
    .cooccurrence__head,
    .cooccurrence__empty {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
