<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HabitStatsResponse, HabitWindow } from '$lib/api/habits';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import type { TagResponse } from '$lib/api/tags';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import HabitDetailBody from '$lib/components/trends/HabitDetailBody.svelte';
  import HabitDetailSheet from '$lib/components/trends/HabitDetailSheet.svelte';

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
  let mobile = false;
  let sheetOpen = false;
  let mobileMedia: MediaQueryList | null = null;

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

  function pct(value: number): string {
    return `${Math.round(value)}%`;
  }

  function metricLabel(metric: string | null | undefined): string {
    if (!metric) return '';
    const key = `trends.metric.${metric}`;
    const translated = $_(key);
    return translated === key ? metric : translated;
  }

  function correlationListLabel(habit: HabitStatsResponse): string {
    if (habit.correlation_score === null) {
      return $_('habits.correlation_pending');
    }
    return $_('habits.correlation_brief', {
      values: {
        score: habit.correlation_score.toFixed(2),
        metric: metricLabel(habit.correlation_metric),
      },
    });
  }

  function selectRow(tagId: string) {
    selectedTagId = tagId;
    if (mobile) {
      sheetOpen = true;
    }
  }

  function handleMobileChange(event: MediaQueryListEvent | MediaQueryList) {
    mobile = event.matches;
    if (!mobile) {
      sheetOpen = false;
    }
  }

  onMount(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    mobileMedia = window.matchMedia('(max-width: 760px)');
    handleMobileChange(mobileMedia);
    mobileMedia.addEventListener('change', handleMobileChange);
  });

  onDestroy(() => {
    mobileMedia?.removeEventListener('change', handleMobileChange);
  });
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
    <div class="habits__layout" class:habits__layout--mobile={mobile}>
      <div class="habits__list" aria-label={$_('habits.list_label')}>
        {#each habitRows as row (row.habit.tag_id)}
          <button
            type="button"
            class:active={row.habit.tag_id === selected?.habit.tag_id}
            on:click={() => selectRow(row.habit.tag_id)}
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
              <strong>{pct(row.habit.adherence_rate)} · {$_('habits.window_last', { values: { n: window } })}</strong>
              <small>{correlationListLabel(row.habit)}</small>
            </span>
          </button>
        {/each}
      </div>

      {#if selected && !mobile}
        <HabitDetailBody
          {selected}
          {detailHeatmap}
          {loading}
          on:selectDate={(event) => dispatch('selectDate', event.detail)}
        />
      {/if}
    </div>
  {/if}
</section>

<HabitDetailSheet
  open={sheetOpen && mobile}
  {selected}
  {detailHeatmap}
  {window}
  {loading}
  on:close={() => (sheetOpen = false)}
  on:selectDate={(event) => dispatch('selectDate', event.detail)}
/>

<style>
  .habits {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    min-width: 0;
    max-width: 100%;
  }

  .habits__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .habits__header h2,
  .habits__header p {
    margin: 0;
  }

  .habits__header h2 {
    font-size: var(--text-lg);
  }

  .habits__header p,
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

  .habits__layout--mobile {
    grid-template-columns: 1fr;
  }

  .habits__list {
    display: grid;
    gap: var(--space-2);
  }

  .habits__list button {
    min-height: 4.25rem;
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
    max-width: 48%;
  }

  .habits__empty {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    padding: var(--space-3);
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

    .habits__metric {
      max-width: 55%;
    }
  }
</style>
