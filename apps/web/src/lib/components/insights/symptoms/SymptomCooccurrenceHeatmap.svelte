<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type {
    InsightMaturityPhase,
    SymptomTagCooccurrenceCell,
    SymptomTagCooccurrenceResponse,
  } from '$lib/api/insights';

  export let data: SymptomTagCooccurrenceResponse | null = null;
  export let loading = false;
  export let phase: InsightMaturityPhase | null = null;

  $: symptoms = data
    ? Array.from(
        new Map(data.cells.map((cell) => [cell.symptom.symptom_id, cell.symptom])).values()
      ).sort((a, b) => a.slug.localeCompare(b.slug))
    : [];
  $: tags = data
    ? Array.from(new Map(data.cells.map((cell) => [cell.tag.tag_id, cell.tag])).values()).sort(
        (a, b) => a.slug.localeCompare(b.slug)
      )
    : [];
  $: cellByKey = new Map(
    (data?.cells ?? []).map((cell) => [`${cell.symptom.symptom_id}:${cell.tag.tag_id}`, cell])
  );
  $: showLift = phase === 'provisional' || phase === 'robust';
  $: showSkeleton = loading && !data;

  function cellLevel(cell: SymptomTagCooccurrenceCell): string {
    if (!showLift) return 'count';
    if (cell.lift >= 2) return 'high-positive';
    if (cell.lift >= 1.5) return 'positive';
    if (cell.lift <= 0.5) return 'high-negative';
    if (cell.lift <= 0.8) return 'negative';
    return 'neutral';
  }

  function cellLabel(cell: SymptomTagCooccurrenceCell): string {
    if (!showLift) return String(cell.co_count);
    return `${cell.lift.toFixed(1)}${cell.p_value_corrected < 0.1 ? '*' : ''}`;
  }
</script>

<section class="symptom-cooccurrence" data-loading={loading ? 'true' : 'false'}>
  <header class="symptom-cooccurrence__header">
    <div>
      <h3>{$_('insights.symptoms.cooccurrence_heading')}</h3>
      <p>{$_('insights.symptoms.cooccurrence_body')}</p>
    </div>
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

        {#each symptoms as symptom}
          <div class="symptom-cooccurrence__row-label" title={symptom.name}>
            {symptom.icon ? `${symptom.icon} ` : ''}{symptom.name}
          </div>
          {#each tags as tag}
            {@const cell = cellByKey.get(`${symptom.symptom_id}:${tag.tag_id}`)}
            {#if cell}
              <div
                class={`symptom-cooccurrence__cell symptom-cooccurrence__cell--${cellLevel(cell)}`}
                role="gridcell"
                title={$_('insights.symptoms.cooccurrence_cell_title', {
                  values: {
                    symptom: symptom.name,
                    tag: tag.name,
                    lift: cell.lift.toFixed(2),
                    count: cell.co_count,
                  },
                })}
              >
                {cellLabel(cell)}
              </div>
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
    gap: 0.2rem;
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
  }

  .symptom-cooccurrence__cell--zero {
    opacity: 0.25;
    background: var(--color-surface-dynamic);
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

  @media (max-width: 520px) {
    .symptom-cooccurrence__grid {
      grid-template-columns: minmax(7rem, 8rem) repeat(var(--tag-count), minmax(3.25rem, 3.75rem));
      gap: 0.3rem;
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
