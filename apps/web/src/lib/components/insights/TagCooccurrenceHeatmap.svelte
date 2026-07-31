<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagCooccurrenceRange, TagCooccurrenceResponse } from '$lib/api/insights';
  import type { CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';
  import {
    buildTagCooccurrenceMatrix,
    cooccurrenceIntensityLevel,
    orderTagCooccurrenceMatrix,
    focusTagCooccurrenceMatrixOnCluster,
    type TagClusterMeta,
  } from '$lib/utils/tagCooccurrenceMatrix';
  import {
    clampCooccurrenceVisibleCount,
    COOCCURRENCE_MIN_VISIBLE,
    defaultCooccurrenceVisibleCount,
    pruneTagCooccurrenceMatrix,
    sliceSquareMatrixByTopStrength,
  } from '$lib/utils/heatmapPruning';
  import EntryLaunchButton from '$lib/components/entries/EntryLaunchButton.svelte';

  export let data: TagCooccurrenceResponse | null = null;
  export let loading = false;
  export let range: TagCooccurrenceRange = '90d';
  export let showRangeSelector = true;
  export let minPairsForDisplay = 5;
  export let sortMode: CooccurrenceSortMode = 'alphabetical';
  export let enableClusterSort = false;
  export let pruneSparseAxes = true;
  /** Server co-occurrence clusters (#489); empty maps when insufficient_data. */
  export let clusterMeta: TagClusterMeta = { byTagId: new Map(), labels: [] };
  /** Focused cluster id, or null for "all". Two-way bound from the page. */
  export let focusedClusterId: number | null = null;
  /**
   * Marketing preview mode (landing product shot): hide the header, cluster and
   * density controls so the heatmap grid is the hero in the narrow frame (#546).
   */
  export let preview = false;

  const dispatch = createEventDispatcher<{
    rangeChange: { range: TagCooccurrenceRange };
    sortModeChange: { sortMode: CooccurrenceSortMode };
    focusClusterChange: { clusterId: number | null };
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
  const COMPACT_QUERY = '(max-width: 480px)';

  let focusedKey: string | null = null;
  let compactViewport = false;
  let visibleCount = 0;
  let densitySignature = '';
  let media: MediaQueryList | null = null;

  function syncCompact(): void {
    compactViewport = media?.matches ?? false;
  }

  onMount(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    media = window.matchMedia(COMPACT_QUERY);
    syncCompact();
    media.addEventListener('change', syncCompact);
  });

  onDestroy(() => {
    media?.removeEventListener('change', syncCompact);
  });

  $: clustersAvailable = clusterMeta.labels.length > 0;
  // A stale focus (cluster no longer present after a range change) resets to all.
  $: if (
    focusedClusterId !== null &&
    !clusterMeta.labels.some((c) => c.cluster_id === focusedClusterId)
  ) {
    focusedClusterId = null;
  }
  $: rawMatrix = data ? buildTagCooccurrenceMatrix(data.pairs) : { tags: [], counts: [] };
  $: orderedMatrix = orderTagCooccurrenceMatrix(rawMatrix, sortMode, clusterMeta.byTagId);
  $: focusedMatrix =
    focusedClusterId !== null
      ? focusTagCooccurrenceMatrixOnCluster(orderedMatrix, clusterMeta.byTagId, focusedClusterId)
      : orderedMatrix;
  $: prunedMatrix = pruneSparseAxes
    ? pruneTagCooccurrenceMatrix(focusedMatrix.tags, focusedMatrix.counts)
    : focusedMatrix;
  $: totalAxes = prunedMatrix.tags.length;
  $: nextDensitySignature = `${data?.start_date ?? ''}:${data?.end_date ?? ''}:${data?.pairs.length ?? 0}:${sortMode}:${pruneSparseAxes}:${compactViewport}:${totalAxes}:${focusedClusterId ?? 'all'}`;
  $: if (nextDensitySignature !== densitySignature) {
    densitySignature = nextDensitySignature;
    visibleCount = defaultCooccurrenceVisibleCount(totalAxes, compactViewport);
  }
  $: effectiveVisible = clampCooccurrenceVisibleCount(visibleCount, totalAxes);
  $: sliced = sliceSquareMatrixByTopStrength(
    prunedMatrix.tags,
    prunedMatrix.counts,
    effectiveVisible
  );
  $: matrix = { tags: sliced.tags, counts: sliced.counts };
  // Boundary flag per axis: true where a tag starts a different cluster than the
  // previous one, so the grid can draw a gap between clusters (#489). Only in
  // clustered mode with clusters present and no single-cluster focus active.
  $: showClusterGaps = sortMode === 'clustered' && clustersAvailable && focusedClusterId === null;
  $: clusterBoundaries = showClusterGaps
    ? matrix.tags.map((tag, index) => {
        if (index === 0) return false;
        return (
          clusterMeta.byTagId.get(tag.tag_id) !==
          clusterMeta.byTagId.get(matrix.tags[index - 1].tag_id)
        );
      })
    : matrix.tags.map(() => false);
  $: showDensityControls = totalAxes > COOCCURRENCE_MIN_VISIBLE;
  $: canDecreaseDensity = effectiveVisible > Math.min(COOCCURRENCE_MIN_VISIBLE, totalAxes);
  $: canIncreaseDensity = effectiveVisible < totalAxes;
  $: maxCount = matrix.counts.flat().reduce((peak, count) => Math.max(peak, count), 0);
  $: hasEnoughPairs = (data?.pairs.length ?? 0) >= minPairsForDisplay;
  $: showSkeleton = loading && !data;
  $: interactiveCells = matrix.tags.flatMap((rowTag, rowIndex) =>
    matrix.tags.flatMap((colTag, colIndex) => {
      if (rowIndex === colIndex) return [];
      const count = matrix.counts[rowIndex]?.[colIndex] ?? 0;
      if (count <= 0) return [];
      const key = `${rowTag.tag_id}:${colTag.tag_id}`;
      return [{ key, rowIndex, colIndex, rowTag, colTag, count }];
    })
  );
  $: if (interactiveCells.length > 0 && !focusedKey) {
    focusedKey = interactiveCells[0]?.key ?? null;
  }

  function rangeLabel(option: TagCooccurrenceRange): string {
    if (option === '30d') return $_('insights.cooccurrence.range_30d');
    if (option === '90d') return $_('insights.cooccurrence.range_90d');
    return $_('insights.cooccurrence.range_1y');
  }

  function toggleSortMode(): void {
    const next = sortMode === 'alphabetical' ? 'clustered' : 'alphabetical';
    dispatch('sortModeChange', { sortMode: next });
  }

  function focusCluster(clusterId: number | null): void {
    focusedClusterId = clusterId;
    dispatch('focusClusterChange', { clusterId });
  }

  function decreaseDensity(): void {
    visibleCount = clampCooccurrenceVisibleCount(effectiveVisible - 1, totalAxes);
  }

  function increaseDensity(): void {
    visibleCount = clampCooccurrenceVisibleCount(effectiveVisible + 1, totalAxes);
  }

  function focusCell(key: string): void {
    focusedKey = key;
    document.querySelector<HTMLButtonElement>(`[data-tag-co-cell="${key}"]`)?.focus();
  }

  function selectPair(
    rowTag: (typeof matrix.tags)[number],
    colTag: (typeof matrix.tags)[number]
  ): void {
    if (!data) return;
    dispatch('selectPair', {
      tagAId: rowTag.tag_id,
      tagBId: colTag.tag_id,
      tagAName: rowTag.name,
      tagBName: colTag.name,
      startDate: data.start_date,
      endDate: data.end_date,
    });
  }

  function handleCellKeydown(
    event: KeyboardEvent,
    key: string,
    rowIndex: number,
    colIndex: number,
    rowTag: (typeof matrix.tags)[number],
    colTag: (typeof matrix.tags)[number]
  ): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectPair(rowTag, colTag);
      return;
    }

    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();

    let next: (typeof interactiveCells)[number] | undefined;
    if (event.key === 'ArrowRight') {
      const index = interactiveCells.findIndex((item) => item.key === key);
      next = interactiveCells[index + 1];
    } else if (event.key === 'ArrowLeft') {
      const index = interactiveCells.findIndex((item) => item.key === key);
      next = interactiveCells[index - 1];
    } else if (event.key === 'ArrowDown') {
      next = interactiveCells.find(
        (item) => item.colIndex === colIndex && item.rowIndex > rowIndex
      );
    } else {
      next = [...interactiveCells]
        .reverse()
        .find((item) => item.colIndex === colIndex && item.rowIndex < rowIndex);
    }

    if (next) focusCell(next.key);
  }
</script>

<section
  class="cooccurrence"
  class:cooccurrence--preview={preview}
  data-loading={loading ? 'true' : 'false'}
>
  {#if !preview}
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
        {#if enableClusterSort}
          <button
            type="button"
            class="cooccurrence__sort"
            data-testid="tag-cooccurrence-sort-toggle"
            on:click={toggleSortMode}
          >
            {sortMode === 'clustered'
              ? $_('insights.cooccurrence.sort_alphabetical')
              : $_('insights.cooccurrence.sort_clustered')}
          </button>
        {/if}
        {#if showRangeSelector}
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
        {/if}
      </div>
    </div>
  {/if}

  {#if !preview && clustersAvailable && data && hasEnoughPairs}
    <div
      class="cooccurrence__clusters"
      role="group"
      aria-label={$_('insights.cooccurrence.focus_label')}
      data-testid="tag-cooccurrence-focus"
    >
      <button
        type="button"
        class="cooccurrence__chip"
        class:cooccurrence__chip--active={focusedClusterId === null}
        aria-pressed={focusedClusterId === null}
        on:click={() => focusCluster(null)}
      >
        {$_('insights.cooccurrence.focus_all')}
      </button>
      {#each clusterMeta.labels as cluster (cluster.cluster_id)}
        <button
          type="button"
          class="cooccurrence__chip"
          class:cooccurrence__chip--active={focusedClusterId === cluster.cluster_id}
          aria-pressed={focusedClusterId === cluster.cluster_id}
          data-testid="tag-cooccurrence-focus-chip"
          on:click={() =>
            focusCluster(focusedClusterId === cluster.cluster_id ? null : cluster.cluster_id)}
        >
          {cluster.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if !preview && showDensityControls && data && hasEnoughPairs && totalAxes > 0}
    <div
      class="cooccurrence__density"
      role="group"
      aria-label={$_('insights.cooccurrence.density_label')}
      data-testid="tag-cooccurrence-density"
    >
      <button
        type="button"
        class="cooccurrence__density-btn"
        data-testid="tag-cooccurrence-density-decrease"
        aria-label={$_('insights.cooccurrence.density_decrease')}
        disabled={!canDecreaseDensity}
        on:click={decreaseDensity}
      >
        −
      </button>
      <span class="cooccurrence__density-status" data-testid="tag-cooccurrence-density-status">
        {$_('insights.cooccurrence.density_showing', {
          values: { visible: effectiveVisible, total: totalAxes },
        })}
      </span>
      <button
        type="button"
        class="cooccurrence__density-btn"
        data-testid="tag-cooccurrence-density-increase"
        aria-label={$_('insights.cooccurrence.density_increase')}
        disabled={!canIncreaseDensity}
        on:click={increaseDensity}
      >
        +
      </button>
    </div>
  {/if}

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
        {#each matrix.tags as colTag, colIndex}
          <div
            class="cooccurrence__col-label"
            class:cooccurrence__boundary-left={clusterBoundaries[colIndex]}
            title={colTag.name}
          >
            {colTag.name}
          </div>
        {/each}

        {#each matrix.tags as rowTag, rowIndex}
          <div
            class="cooccurrence__row-label"
            class:cooccurrence__boundary-top={clusterBoundaries[rowIndex]}
            title={rowTag.name}
          >
            {rowTag.name}
          </div>
          {#each matrix.tags as colTag, colIndex}
            {@const count = matrix.counts[rowIndex]?.[colIndex] ?? 0}
            {@const level = cooccurrenceIntensityLevel(count, maxCount)}
            {#if rowIndex === colIndex}
              <div
                class="cooccurrence__cell cooccurrence__cell--empty"
                class:cooccurrence__boundary-left={clusterBoundaries[colIndex]}
                class:cooccurrence__boundary-top={clusterBoundaries[rowIndex]}
                role="gridcell"
                aria-hidden="true"
              ></div>
            {:else if count > 0}
              {@const cellKey = `${rowTag.tag_id}:${colTag.tag_id}`}
              <button
                type="button"
                class={`cooccurrence__cell cooccurrence__cell--${level}`}
                class:cooccurrence__boundary-left={clusterBoundaries[colIndex]}
                class:cooccurrence__boundary-top={clusterBoundaries[rowIndex]}
                role="gridcell"
                tabindex={focusedKey === cellKey ? 0 : -1}
                data-tag-co-cell={cellKey}
                data-testid="tag-cooccurrence-cell"
                aria-label={$_('insights.cooccurrence.cell_aria', {
                  values: { tagA: rowTag.name, tagB: colTag.name, count },
                })}
                title={$_('insights.cooccurrence.cell_title', {
                  values: { tagA: rowTag.name, tagB: colTag.name, count },
                })}
                on:click={() => selectPair(rowTag, colTag)}
                on:keydown={(event) =>
                  handleCellKeydown(event, cellKey, rowIndex, colIndex, rowTag, colTag)}
              >
                <span>{count}</span>
              </button>
            {:else}
              <div
                class="cooccurrence__cell cooccurrence__cell--zero"
                class:cooccurrence__boundary-left={clusterBoundaries[colIndex]}
                class:cooccurrence__boundary-top={clusterBoundaries[rowIndex]}
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
      <EntryLaunchButton>{$_('trends.empty_cta')}</EntryLaunchButton>
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
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
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
    border: none;
    background: transparent;
    cursor: pointer;
  }

  .cooccurrence__sort {
    margin-right: var(--space-1);
    color: var(--color-primary) !important;
  }

  .cooccurrence__range--active {
    background: var(--color-primary-highlight);
    color: var(--color-primary) !important;
  }

  .cooccurrence__clusters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    align-items: center;
  }

  .cooccurrence__chip {
    min-height: 44px;
    padding: 0 var(--space-3);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    cursor: pointer;
  }

  .cooccurrence__chip--active {
    border-color: var(--color-primary);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
  }

  .cooccurrence__chip:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  /* Cluster group gap (#489): a leading margin plus a faint rule opens space
     where a new cluster begins on each axis. */
  .cooccurrence__boundary-left {
    margin-left: var(--space-2);
    box-shadow: inset 1px 0 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent);
  }

  .cooccurrence__boundary-top {
    margin-top: var(--space-2);
    box-shadow: inset 0 1px 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent);
  }

  .cooccurrence__boundary-left.cooccurrence__boundary-top {
    box-shadow:
      inset 1px 0 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent),
      inset 0 1px 0 0 color-mix(in srgb, var(--color-primary) 30%, transparent);
  }

  .cooccurrence__density {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-1);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    align-self: flex-start;
  }

  .cooccurrence__density-btn {
    min-width: 44px;
    min-height: 44px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-primary);
    font-size: var(--text-lg);
    font-weight: 700;
    cursor: pointer;
  }

  .cooccurrence__density-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .cooccurrence__density-status {
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-text-muted);
    min-width: 4.5rem;
    text-align: center;
  }

  .cooccurrence__scroller {
    overflow: auto;
    max-width: 100%;
  }

  .cooccurrence__grid {
    display: grid;
    grid-template-columns: minmax(6rem, 8rem) repeat(var(--tag-count), minmax(2.75rem, 1fr));
    gap: var(--heatmap-matrix-gap);
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
    display: flex;
    align-items: flex-end;
    justify-content: center;
    min-height: 6.5rem;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    text-align: left;
    padding: var(--space-2) 0 var(--space-1);
    max-height: 7rem;
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

  /* Marketing preview (#546): no header/controls, tighter padding and shorter
     column labels so the grid of cells is the hero in the narrow product shot. */
  .cooccurrence--preview {
    gap: var(--space-2);
    padding: var(--space-3);
  }

  .cooccurrence--preview .cooccurrence__col-label {
    min-height: 3.25rem;
    max-height: 4rem;
  }

  /* Smaller cells + narrower label column, and drop the app's max-content min-width
     so the whole grid shrinks to fit the product-shot column (incl. mobile) rather
     than scrolling out of view (#546). */
  .cooccurrence--preview .cooccurrence__grid {
    grid-template-columns: minmax(3rem, 4.5rem) repeat(var(--tag-count), minmax(2rem, 1fr));
    min-width: 0;
  }

  .cooccurrence--preview .cooccurrence__cell {
    min-width: 2rem;
    min-height: 2rem;
  }

  @media (max-width: 480px) {
    .cooccurrence__head,
    .cooccurrence__empty {
      flex-direction: column;
      align-items: stretch;
    }

    .cooccurrence__density {
      align-self: stretch;
      justify-content: space-between;
    }

    .cooccurrence__grid {
      grid-template-columns: minmax(7rem, 8rem) repeat(var(--tag-count), minmax(3.25rem, 3.75rem));
      gap: var(--heatmap-matrix-gap-mobile);
    }

    .cooccurrence__corner,
    .cooccurrence__row-label {
      position: static;
    }

    .cooccurrence__col-label {
      min-height: 3.25rem;
      max-height: none;
      writing-mode: horizontal-tb;
      transform: none;
      align-items: flex-end;
      justify-content: center;
      padding: 0 0 var(--space-1);
      text-align: center;
      white-space: normal;
      overflow-wrap: anywhere;
      line-height: 1.05;
    }

    .cooccurrence__row-label {
      padding-right: var(--space-1);
      white-space: normal;
      line-height: 1.05;
    }

    .cooccurrence__cell {
      min-width: 3.25rem;
    }
  }
</style>
