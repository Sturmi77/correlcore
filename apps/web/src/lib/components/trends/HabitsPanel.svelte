<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HabitStatsResponse, HabitWindow } from '$lib/api/habits';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import type { TagResponse } from '$lib/api/tags';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import TagHeatmap from '$lib/components/trends/TagHeatmap.svelte';

  export let habits: HabitStatsResponse[] = [];
  export let tags: TagResponse[] = [];
  export let heatmap: TagHeatmapResponse | null = null;
  export let window: HabitWindow = 28;
  export let loading = false;

  const dispatch = createEventDispatcher<{
    windowChange: { window: HabitWindow };
    selectDate: { date: string; tagId: string };
  }>();

  const windowOptions: HabitWindow[] = [7, 14, 28, 90];
  let selectedTagId: string | null = null;

  $: tagById = new Map(tags.map((tag) => [tag.id, tag]));
  $: habitRows = habits
    .map((habit) => ({ habit, tag: tagById.get(habit.tag_id) }))
    .filter((row): row is { habit: HabitStatsResponse; tag: TagResponse } => Boolean(row.tag));
  $: selected = habitRows.find((row) => row.habit.tag_id === selectedTagId) ?? habitRows[0] ?? null;
  $: detailHeatmap =
    selected && heatmap
      ? { ...heatmap, tags: heatmap.tags.filter((tag) => tag.tag_id === selected.habit.tag_id) }
      : null;
  $: controlOptions = windowOptions.map(
    (value): SegmentedControlOption => ({
      id: String(value),
      label: $_('habits.window_days', { values: { n: value } }),
      testId: `habits-window-${value}`,
    })
  );

  function statusKey(habit: HabitStatsResponse): string {
    if (habit.habit_type === 'reduce' && habit.days_tracked <= habit.target_days) {
      return 'habits.status.within_target';
    }
    if (habit.habit_type === 'reduce') {
      return 'habits.status.above_target';
    }
    return 'habits.status.progress';
  }

  function pct(value: number): string {
    return `${Math.round(value)}%`;
  }
</script>

<section class="habits" data-testid="habits-panel">
  <header class="habits__header">
    <div>
      <h2>{$_('habits.heading')}</h2>
      <p>{$_('habits.subtitle')}</p>
    </div>
    <SegmentedControl
      value={String(window)}
      options={controlOptions}
      ariaLabel={$_('habits.window_label')}
      testId="habits-window-control"
      on:change={(event) =>
        dispatch('windowChange', { window: Number(event.detail.value) as HabitWindow })}
    />
  </header>

  {#if loading && habitRows.length === 0}
    <p class="habits__state" role="status">{$_('habits.loading')}</p>
  {:else if habitRows.length === 0}
    <div class="habits__empty">
      <p>{$_('habits.empty')}</p>
      <a class="btn btn-sm variant-soft-primary" href="/settings/tags">{$_('habits.empty_cta')}</a>
    </div>
  {:else}
    <div class="habits__layout">
      <div class="habits__list" aria-label={$_('habits.list_label')}>
        {#each habitRows as row (row.habit.tag_id)}
          <button
            type="button"
            class:active={row.habit.tag_id === selected?.habit.tag_id}
            on:click={() => (selectedTagId = row.habit.tag_id)}
            data-testid={`habit-row-${row.habit.tag_id}`}
          >
            <span class="habits__row-title">
              <strong>{row.tag.name}</strong>
              <small
                >{$_(`tag.category.${row.tag.category}`)} · {$_(
                  `habits.type.${row.habit.habit_type}`
                )}</small
              >
            </span>
            <span class="habits__metric">
              <strong>{pct(row.habit.adherence_rate)}</strong>
              <small>{$_(statusKey(row.habit))}</small>
            </span>
          </button>
        {/each}
      </div>

      {#if selected}
        <article class="habits__detail" data-testid="habit-detail">
          <div class="habits__detail-head">
            <div>
              <h3>{selected.tag.name}</h3>
              <p>{$_(`habits.type.${selected.habit.habit_type}`)}</p>
            </div>
            <strong>{pct(selected.habit.adherence_rate)}</strong>
          </div>

          <dl class="habits__stats">
            <div>
              <dt>{$_('habits.days_tracked')}</dt>
              <dd>{selected.habit.days_tracked}/{selected.habit.days_total}</dd>
            </div>
            <div>
              <dt>{$_('habits.target_days')}</dt>
              <dd>{selected.habit.target_days}</dd>
            </div>
            <div>
              <dt>{$_('habits.target_frequency')}</dt>
              <dd>{selected.habit.target_frequency}/7</dd>
            </div>
          </dl>

          {#if selected.habit.correlation_score !== null}
            <section class="habits__correlation">
              <span>{$_('habits.correlation')}</span>
              <strong>{selected.habit.correlation_score.toFixed(2)}</strong>
            </section>
          {/if}

          <TagHeatmap
            heatmap={detailHeatmap}
            {loading}
            compact
            on:selectDate={(event) => dispatch('selectDate', event.detail)}
          />
        </article>
      {/if}
    </div>
  {/if}
</section>

<style>
  .habits {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    min-width: 0;
    max-width: 100%;
  }

  .habits__header,
  .habits__detail-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .habits__header h2,
  .habits__header p,
  .habits__detail h3,
  .habits__detail p {
    margin: 0;
  }

  .habits__header h2,
  .habits__detail h3 {
    font-size: var(--text-lg);
  }

  .habits__header p,
  .habits__detail p,
  .habits__state,
  .habits__empty {
    color: var(--color-text-muted);
  }

  .habits__layout {
    display: grid;
    grid-template-columns: minmax(15rem, 0.75fr) minmax(0, 1.25fr);
    gap: var(--space-4);
    align-items: start;
    min-width: 0;
  }

  .habits__list {
    display: grid;
    gap: var(--space-2);
  }

  .habits__list button {
    min-height: 4rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    color: var(--color-text);
    padding: var(--space-3);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    text-align: left;
  }

  .habits__list button.active,
  .habits__list button:focus-visible {
    border-color: var(--color-primary);
    outline: 2px solid color-mix(in srgb, var(--color-primary) 24%, transparent);
    outline-offset: 1px;
  }

  .habits__row-title,
  .habits__metric {
    display: grid;
    gap: 0.15rem;
  }

  .habits__row-title {
    min-width: 0;
  }

  .habits__row-title strong,
  .habits__row-title small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .habits__row-title small,
  .habits__metric small {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .habits__metric {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .habits__detail {
    display: grid;
    gap: var(--space-4);
    min-width: 0;
  }

  .habits__detail-head > strong {
    font-size: 2rem;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  .habits__stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
    margin: 0;
  }

  .habits__stats div,
  .habits__correlation,
  .habits__empty {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    padding: var(--space-3);
  }

  .habits__stats dt,
  .habits__correlation span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .habits__stats dd {
    margin: 0.2rem 0 0;
    font-weight: 650;
  }

  .habits__correlation {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .habits__empty {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .habits__empty p {
    margin: 0;
  }

  @media (max-width: 760px) {
    .habits__header,
    .habits__empty {
      align-items: stretch;
      flex-direction: column;
    }

    .habits__layout {
      grid-template-columns: 1fr;
    }

    .habits__detail {
      border-radius: var(--radius-md) var(--radius-md) 0 0;
      border: 1px solid var(--color-border-chart);
      background: var(--color-surface-chart-bg);
      padding: var(--space-3);
      overflow-x: auto;
    }

    .habits__stats {
      grid-template-columns: 1fr;
    }
  }
</style>
