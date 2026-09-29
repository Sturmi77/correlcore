<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagCooccurrenceRange, TagCooccurrenceResponse } from '$lib/api/insights';
  import type { CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';
  import {
    buildTagCooccurrenceMatrix,
    cooccurrenceDenominators,
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
  export let error = false;
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
  $: rawMatrix = data ? buildTagCooccurrenceMatrix(data.pairs ?? []) : { tags: [], counts: [] };
  $: orderedMatrix = orderTagCooccurrenceMatrix(rawMatrix, sortMode, clusterMeta.byTagId);
  $: focusedMatrix =
    focusedClusterId !== null
      ? focusTagCooccurrenceMatrixOnCluster(orderedMatrix, clusterMeta.byTagId, focusedClusterId)
      : orderedMatrix;
  $: prunedMatrix = pruneSparseAxes
    ? pruneTagCooccurrenceMatrix(focusedMatrix.tags, focusedMatrix.counts)
    : focusedMatrix;
  $: totalAxes = prunedMatrix.tags.length;
  $: nextDensitySignature = `${data?.start_date ?? ''}:${data?.end_date ?? ''}:${data?.pairs?.length ?? 0}:${sortMode}:${pruneSparseAxes}:${compactViewport}:${totalAxes}:${focusedClusterId ?? 'all'}`;
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
  $: hasEnoughPairs = (data?.pairs?.length ?? 0) >= minPairsForDisplay;
  $: showSkeleton = loading && !data;
  $: analysisUnavailable =
    data?.analysis_status === 'limit_exceeded' ||
    data?.analysis_status === 'busy' ||
    data?.analysis_status === 'timeout' ||
    data?.analysis_status === 'unavailable';
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

  function pairEvidence(
    tagAId: string,
    tagBId: string,
    count: number
  ): { aTotal: number; bTotal: number } {
    const pair = data?.pairs.find(
      (item) =>
        (item.tag_a.tag_id === tagAId && item.tag_b.tag_id === tagBId) ||
        (item.tag_a.tag_id === tagBId && item.tag_b.tag_id === tagAId)
    );
    if (!pair) return { aTotal: count, bTotal: count };
    // pct_of_* are oriented to tag_a / tag_b as returned by the API.
    if (pair.tag_a.tag_id === tagAId) {
      return cooccurrenceDenominators(pair.count, pair.pct_of_a, pair.pct_of_b);
    }
    return cooccurrenceDenominators(pair.count, pair.pct_of_b, pair.pct_of_a);
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
              {@const evidence = pairEvidence(rowTag.tag_id, colTag.tag_id, count)}
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
                  values: {
                    tagA: rowTag.name,
                    tagB: colTag.name,
                    count,
                    aTotal: evidence.aTotal,
                    bTotal: evidence.bTotal,
                  },
                })}
                title={$_('insights.cooccurrence.cell_title', {
                  values: {
                    tagA: rowTag.name,
                    tagB: colTag.name,
                    count,
                    aTotal: evidence.aTotal,
                    bTotal: evidence.bTotal,
                  },
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
    </div>
  {:else if !loading && analysisUnavailable}
    <div class="cooccurrence__empty" data-testid="cooccurrence-analysis-unavailable">
      <p>{$_(`insights.cooccurrence.status_${data?.analysis_status}`)}</p>
