<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type {
    InsightMaturityPhase,
    SymptomTagCooccurrenceCell,
    SymptomTagCooccurrenceResponse,
  } from '$lib/api/insights';
  import { orderAxisIds, type CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';

  export let data: SymptomTagCooccurrenceResponse | null = null;
  export let loading = false;
  export let phase: InsightMaturityPhase | null = null;
  export let sortMode: CooccurrenceSortMode = 'alphabetical';
  export let hideHeading = false;

  const dispatch = createEventDispatcher<{ selectCell: { cell: SymptomTagCooccurrenceCell } }>();

  let focusedKey: string | null = null;

  $: symptomProfiles = buildProfiles(data, 'symptom');
  $: tagProfiles = buildProfiles(data, 'tag');
  $: symptomIds = data
    ? orderAxisIds(
        Array.from(
          new Map(data.cells.map((cell) => [cell.symptom.symptom_id, cell.symptom])).keys()
        ),
        symptomProfiles,
        sortMode,
        (id) => data!.cells.find((cell) => cell.symptom.symptom_id === id)?.symptom.slug ?? id
      )
    : [];
  $: tagIds = data
    ? orderAxisIds(
        Array.from(new Map(data.cells.map((cell) => [cell.tag.tag_id, cell.tag])).keys()),
        tagProfiles,
        sortMode,
        (id) => data!.cells.find((cell) => cell.tag.tag_id === id)?.tag.slug ?? id
      )
    : [];
  $: symptoms = symptomIds
    .map((id) => data?.cells.find((cell) => cell.symptom.symptom_id === id)?.symptom)
    .filter((symptom): symptom is SymptomTagCooccurrenceCell['symptom'] => Boolean(symptom));
  $: tags = tagIds
    .map((id) => data?.cells.find((cell) => cell.tag.tag_id === id)?.tag)
    .filter((tag): tag is SymptomTagCooccurrenceCell['tag'] => Boolean(tag));
  $: cellByKey = new Map(
    (data?.cells ?? []).map((cell) => [`${cell.symptom.symptom_id}:${cell.tag.tag_id}`, cell])
  );
  $: showLift = phase === 'provisional' || phase === 'robust';
  $: showSkeleton = loading && !data;
  $: interactiveCells = symptoms.flatMap((symptom, rowIndex) =>
    tags.flatMap((tag, colIndex) => {
      const cell = cellByKey.get(`${symptom.symptom_id}:${tag.tag_id}`);
      if (!cell) return [];
      const key = `${symptom.symptom_id}:${tag.tag_id}`;
      return [{ key, rowIndex, colIndex, cell, symptom, tag }];
    })
  );
  $: if (interactiveCells.length > 0 && !focusedKey) {
    focusedKey = interactiveCells[0]?.key ?? null;
  }

  function buildProfiles(
    payload: SymptomTagCooccurrenceResponse | null,
    axis: 'symptom' | 'tag'
  ): Map<string, number[]> {
    const profiles = new Map<string, number[]>();
    if (!payload) return profiles;

    const axisIds =
      axis === 'symptom'
        ? [...new Set(payload.cells.map((cell) => cell.symptom.symptom_id))]
        : [...new Set(payload.cells.map((cell) => cell.tag.tag_id))];
    const crossIds =
      axis === 'symptom'
        ? [...new Set(payload.cells.map((cell) => cell.tag.tag_id))]
        : [...new Set(payload.cells.map((cell) => cell.symptom.symptom_id))];

    for (const axisId of axisIds) {
      profiles.set(
        axisId,
        crossIds.map((crossId) => {
          const cell = payload.cells.find((candidate) =>
            axis === 'symptom'
              ? candidate.symptom.symptom_id === axisId && candidate.tag.tag_id === crossId
              : candidate.tag.tag_id === axisId && candidate.symptom.symptom_id === crossId
          );
          return cell?.jaccard ?? 0;
        })
      );
    }

    return profiles;
  }

  function cellLevel(cell: SymptomTagCooccurrenceCell): string {
    if (!showLift) return 'count';
    if (cell.confounder === 'weekday') return 'confounded';
    if (cell.lift >= 2) return 'high-positive';
    if (cell.lift >= 1.5) return 'positive';
    if (cell.lift <= 0.5) return 'high-negative';
    if (cell.lift <= 0.8) return 'negative';
    return 'neutral';
  }

  function cellPrimaryLabel(cell: SymptomTagCooccurrenceCell): string {
    if (!showLift) return String(cell.co_count);
    return `${cell.lift.toFixed(1)}${cell.p_value_corrected < 0.1 ? '*' : ''}`;
  }

  function cellAriaLabel(
    cell: SymptomTagCooccurrenceCell,
    symptomName: string,
    tagName: string
  ): string {
    const base = $_('insights.symptoms.cooccurrence_cell_base_rate', {
      values: {
        symptom: symptomName,
        tag: tagName,
        co: cell.co_count,
        symptomDays: cell.symptom_count,
        tagDays: cell.tag_count,
        lift: cell.lift.toFixed(2),
      },
    });
    if (cell.confounder === 'weekday') {
      return `${base} ${$_('insights.weekday_confounded_note')}`;
    }
    return base;
  }

  function selectCell(cell: SymptomTagCooccurrenceCell): void {
    dispatch('selectCell', { cell });
  }

  function focusCell(key: string): void {
    focusedKey = key;
    const node = document.querySelector<HTMLButtonElement>(`[data-symptom-co-cell="${key}"]`);
    node?.focus();
  }

  function handleCellKeydown(
    event: KeyboardEvent,
    key: string,
    rowIndex: number,
    colIndex: number
  ): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      const cell = cellByKey.get(key);
      if (cell) selectCell(cell);
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

<section class="symptom-cooccurrence" data-loading={loading ? 'true' : 'false'}>
  <header
    class="symptom-cooccurrence__header"
    class:symptom-cooccurrence__header--compact={hideHeading}
  >
    {#if !hideHeading}
      <div>
        <h3>{$_('insights.symptoms.cooccurrence_heading')}</h3>
        <p>{$_('insights.symptoms.cooccurrence_body')}</p>
      </div>
    {:else}
      <p>{$_('insights.symptoms.cooccurrence_body')}</p>
    {/if}
  </header>

  {#if showSkeleton}
    <div class="symptom-cooccurrence__skeleton" role="status">
      <span></span>
      <span></span>
      <span></span>
    </div>
  {:else if symptoms.length > 0 && tags.length > 0}
    <div
      class="symptom-cooccurrence__scroller"
      aria-label={$_('insights.symptoms.cooccurrence_aria')}
    >
      <div class="symptom-cooccurrence__grid" style={`--tag-count: ${tags.length}`} role="grid">
        <div class="symptom-cooccurrence__corner" role="presentation"></div>
        {#each tags as tag}
          <div class="symptom-cooccurrence__col-label" title={tag.name}>{tag.name}</div>
        {/each}

        {#each symptoms as symptom, rowIndex}
          <div class="symptom-cooccurrence__row-label" title={symptom.name}>
            {symptom.icon ? `${symptom.icon} ` : ''}{symptom.name}
          </div>
          {#each tags as tag, colIndex}
            {@const cell = cellByKey.get(`${symptom.symptom_id}:${tag.tag_id}`)}
            {@const cellKey = `${symptom.symptom_id}:${tag.tag_id}`}
            {#if cell}
              <button
                type="button"
                class={`symptom-cooccurrence__cell symptom-cooccurrence__cell--${cellLevel(cell)}`}
                role="gridcell"
                tabindex={focusedKey === cellKey ? 0 : -1}
                data-symptom-co-cell={cellKey}
                data-testid="symptom-cooccurrence-cell"
                aria-label={cellAriaLabel(cell, symptom.name, tag.name)}
                title={cellAriaLabel(cell, symptom.name, tag.name)}
                on:click={() => selectCell(cell)}
                on:keydown={(event) => handleCellKeydown(event, cellKey, rowIndex, colIndex)}
              >
                <span class="symptom-cooccurrence__primary">{cellPrimaryLabel(cell)}</span>
                {#if showLift}
                  <sub class="symptom-cooccurrence__sub">{cell.co_count}</sub>
                {/if}
              </button>
            {:else}
              <div
                class="symptom-cooccurrence__cell symptom-cooccurrence__cell--zero"
                role="gridcell"
                aria-hidden="true"
              ></div>
            {/if}
          {/each}
        {/each}
      </div>
    </div>
    <p class="symptom-cooccurrence__legend">
      {showLift
        ? $_('insights.symptoms.cooccurrence_lift_legend')
        : $_('insights.symptoms.cooccurrence_count_legend')}
      {#if showLift && symptoms.some( (symptom) => tags.some((tag) => cellByKey.get(`${symptom.symptom_id}:${tag.tag_id}`)?.confounder === 'weekday') )}
        {' '}{$_('insights.symptoms.cooccurrence_confounder_note')}
      {/if}
    </p>
  {:else if !loading}
    <p class="symptom-cooccurrence__empty">{$_('insights.symptoms.cooccurrence_empty')}</p>
  {/if}
</section>

<style>
  .symptom-cooccurrence {
    display: grid;
    gap: var(--space-3);
  }

  .symptom-cooccurrence__header h3,
  .symptom-cooccurrence__header p,
  .symptom-cooccurrence__legend,
  .symptom-cooccurrence__empty {
    margin: 0;
  }

  .symptom-cooccurrence__header h3 {
    font-size: var(--text-base);
  }

  .symptom-cooccurrence__header p,
  .symptom-cooccurrence__legend,
  .symptom-cooccurrence__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-cooccurrence__scroller {
    overflow: auto;
    max-width: 100%;
  }

  .symptom-cooccurrence__grid {
    display: grid;
    grid-template-columns: minmax(7rem, 10rem) repeat(var(--tag-count), minmax(3rem, 1fr));
    gap: var(--heatmap-matrix-gap);
    min-width: max-content;
  }

  .symptom-cooccurrence__corner,
  .symptom-cooccurrence__row-label {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--color-surface-chart-bg);
  }

  .symptom-cooccurrence__col-label,
  .symptom-cooccurrence__row-label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .symptom-cooccurrence__col-label {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    min-height: 6.5rem;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    padding: var(--space-2) 0 var(--space-1);
    max-height: 7rem;
  }

  .symptom-cooccurrence__row-label {
    display: flex;
    align-items: center;
    padding-right: var(--space-2);
  }

  .symptom-cooccurrence__cell {
    min-width: 3rem;
    min-height: 2.75rem;
    display: grid;
    place-items: center;
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-sm);
    color: var(--color-text);
    font-size: var(--text-xs);
    font-weight: 700;
    cursor: pointer;
    padding: 0;
    background: transparent;
  }

  .symptom-cooccurrence__cell:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .symptom-cooccurrence__primary {
    line-height: 1;
  }

  .symptom-cooccurrence__sub {
    font-size: 0.65rem;
    font-weight: 600;
    color: var(--color-text-muted);
    margin-top: 0.1rem;
  }

  .symptom-cooccurrence__cell--zero {
    opacity: 0.25;
    background: var(--color-surface-dynamic);
    cursor: default;
  }

  .symptom-cooccurrence__cell--count,
  .symptom-cooccurrence__cell--neutral {
    background: color-mix(in srgb, var(--color-primary) 24%, var(--color-surface-dynamic));
  }

  .symptom-cooccurrence__cell--positive {
    background: color-mix(in srgb, var(--color-warning) 36%, var(--color-surface-dynamic));
  }

  .symptom-cooccurrence__cell--high-positive {
    background: color-mix(in srgb, var(--color-warning) 58%, var(--color-surface-dynamic));
  }

  .symptom-cooccurrence__cell--negative {
    background: color-mix(in srgb, var(--color-primary) 32%, var(--color-surface-dynamic));
  }

  .symptom-cooccurrence__cell--high-negative {
    background: color-mix(in srgb, var(--color-primary) 52%, var(--color-surface-dynamic));
  }

  .symptom-cooccurrence__cell--confounded {
    opacity: 0.55;
    background: color-mix(in srgb, var(--color-text-muted) 28%, var(--color-surface-dynamic));
    border-style: dashed;
  }

  @media (max-width: 520px) {
    .symptom-cooccurrence__grid {
      grid-template-columns: minmax(7rem, 8rem) repeat(var(--tag-count), minmax(3.25rem, 3.75rem));
      gap: var(--heatmap-matrix-gap-mobile);
    }

    .symptom-cooccurrence__corner,
    .symptom-cooccurrence__row-label {
      position: static;
    }

    .symptom-cooccurrence__col-label {
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

    .symptom-cooccurrence__row-label {
      padding-right: var(--space-1);
      white-space: normal;
      line-height: 1.05;
    }

    .symptom-cooccurrence__cell {
      min-width: 3.25rem;
    }
  }

  .symptom-cooccurrence__skeleton {
    display: grid;
    gap: var(--space-2);
  }

  .symptom-cooccurrence__skeleton span {
    min-height: 1.5rem;
    border-radius: var(--radius-sm);
    background: var(--color-surface-dynamic);
  }
</style>
