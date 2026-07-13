<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HabitStatsResponse, HabitWindow } from '$lib/api/habits';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import { updateTag, type HabitType, type TagResponse } from '$lib/api/tags';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import HabitDetailBody from '$lib/components/trends/HabitDetailBody.svelte';
  import HabitDetailSheet from '$lib/components/trends/HabitDetailSheet.svelte';
  import {
    formatHabitDelta,
    habitGoalI18nKey,
    habitMetricI18nKey,
    habitProgressValue,
    habitStatusI18nKey,
  } from '$lib/utils/habitMetrics';
  import Minus from 'lucide-svelte/icons/minus';
  import TrendingDown from 'lucide-svelte/icons/trending-down';
  import TrendingUp from 'lucide-svelte/icons/trending-up';

  export let habits: HabitStatsResponse[] = [];
  export let tags: TagResponse[] = [];
  export let availableTags: TagResponse[] = [];
  export let heatmap: TagHeatmapResponse | null = null;
  export let window: HabitWindow = 28;
  export let loading = false;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string; tagId: string };
    habitSetup: void;
  }>();

  let selectedTagId: string | null = null;
  let mobile = false;
  let sheetOpen = false;
  let mobileMedia: MediaQueryList | null = null;
  let setupTagId = '';
  let setupHabitType: HabitType = 'build';
  let setupTargetFrequency = 3;
  let setupSaving = false;
  let setupError = '';

  $: setupCandidates = availableTags.filter((tag) => tag.habit_type === 'none');
  $: canSubmitHabitSetup =
    setupTagId !== '' &&
    setupHabitType !== 'none' &&
    setupTargetFrequency >= 1 &&
    setupTargetFrequency <= 7;

  $: tagById = new Map(tags.map((tag) => [tag.id, tag]));
  $: habitRows = habits
    .map((habit) => ({ habit, tag: tagById.get(habit.tag_id) }))
    .filter((row): row is { habit: HabitStatsResponse; tag: TagResponse } => Boolean(row.tag));
  $: selected = habitRows.find((row) => row.habit.tag_id === selectedTagId) ?? habitRows[0] ?? null;
  $: detailHeatmap =
    selected && heatmap
      ? { ...heatmap, tags: heatmap.tags.filter((tag) => tag.tag_id === selected.habit.tag_id) }
      : null;

  function pct(value: number): string {
    return `${Math.round(value)}%`;
  }

  function metricLabel(metric: string | null | undefined): string {
    const key = habitMetricI18nKey(metric);
    if (!key) return '';
    const translated = $_(key);
    return translated === key ? (metric ?? '') : translated;
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

  function goalLabel(habit: HabitStatsResponse): string {
    return $_(habitGoalI18nKey(habit), {
      values: {
        tracked: habit.days_tracked,
        target: habit.target_days,
      },
    });
  }

  function trendLabel(habit: HabitStatsResponse): string {
    if (habit.adherence_delta === null || habit.trend_direction === 'unknown') {
      return '';
    }
    return $_('habits.trend.delta', {
      values: {
        delta: formatHabitDelta(habit.adherence_delta),
      },
    });
  }

  function selectRow(tagId: string) {
    selectedTagId = tagId;
    if (mobile) {
      sheetOpen = true;
    }
  }

  async function submitHabitSetup(): Promise<void> {
    if (!canSubmitHabitSetup) return;
    setupSaving = true;
    setupError = '';
    try {
      await updateTag(setupTagId, {
        habit_type: setupHabitType,
        target_frequency: setupTargetFrequency,
      });
      setupTagId = '';
      setupHabitType = 'build';
      setupTargetFrequency = 3;
      dispatch('habitSetup');
    } catch (err) {
      setupError = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      setupSaving = false;
    }
  }

  function handleMobileChange(event: MediaQueryListEvent | MediaQueryList) {
    mobile = event.matches;
    if (!mobile) {
      sheetOpen = false;
    }
  }

  onMount(() => {
    const browserWindow = globalThis.window;
    if (!browserWindow || typeof browserWindow.matchMedia !== 'function') {
      return;
    }
    const media = browserWindow.matchMedia('(max-width: 760px)');
    mobileMedia = media;
    handleMobileChange(media);
    media.addEventListener('change', handleMobileChange);
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
      <p class="habits__window" data-testid="habits-window-label">
        {$_('habits.window_last', { values: { n: window } })}
      </p>
    </div>
  </header>

  {#if loading && habitRows.length === 0}
    <p class="habits__state" role="status">{$_('habits.loading')}</p>
  {:else if habitRows.length === 0}
    <div class="habits__empty" data-testid="habits-empty-setup">
      <p class="habits__empty-lead">{$_('habits.empty_setup_body')}</p>
      {#if setupError}
        <InlineAlert variant="error" message={setupError} />
      {/if}
      {#if setupCandidates.length === 0}
        <p>{$_('habits.empty_no_tags')}</p>
        <a class="btn btn-sm btn--secondary" href="/settings/tags">{$_('habits.empty_cta')}</a
        >
      {:else}
        <form class="habits__setup" on:submit|preventDefault={submitHabitSetup}>
          <label>
            <span>{$_('habits.setup_tag_label')}</span>
            <select class="input" bind:value={setupTagId} data-testid="habits-setup-tag">
              <option value="">{$_('habits.setup_tag_placeholder')}</option>
              {#each setupCandidates as tag (tag.id)}
                <option value={tag.id}>{tag.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span>{$_('settings.tags.habit_type')}</span>
            <select class="input" bind:value={setupHabitType} data-testid="habits-setup-type">
              <option value="build">{$_('settings.tags.habit_build')}</option>
              <option value="reduce">{$_('settings.tags.habit_reduce')}</option>
            </select>
          </label>
          <label>
            <span>{$_('settings.tags.target_frequency')}</span>
            <input
              class="input"
              type="number"
              min="1"
              max="7"
              bind:value={setupTargetFrequency}
              data-testid="habits-setup-frequency"
            />
          </label>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            loading={setupSaving}
            disabled={!canSubmitHabitSetup || setupSaving}
            data-testid="habits-setup-submit"
          >
            {$_('habits.setup_submit')}
          </Button>
        </form>
      {/if}
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
            <span class="habits__row-body">
              <span class="habits__goal">
                <span>{goalLabel(row.habit)}</span>
                <strong>{pct(row.habit.adherence_rate)}</strong>
              </span>
              <span
                class="habits__row-bar"
                aria-hidden="true"
                style={`--habit-progress: ${habitProgressValue(row.habit)}%`}
              >
                <span></span>
              </span>
              <span class="habits__row-meta">
                <small>{$_(habitStatusI18nKey(row.habit))}</small>
                {#if trendLabel(row.habit)}
                  <small
                    class:habits__trend--up={row.habit.trend_direction === 'up'}
                    class:habits__trend--down={row.habit.trend_direction === 'down'}
                    class:habits__trend--flat={row.habit.trend_direction === 'flat'}
                    class="habits__trend"
                  >
                    {#if row.habit.trend_direction === 'up'}
                      <TrendingUp size={14} aria-hidden="true" />
                    {:else if row.habit.trend_direction === 'down'}
                      <TrendingDown size={14} aria-hidden="true" />
                    {:else}
                      <Minus size={14} aria-hidden="true" />
                    {/if}
                    {trendLabel(row.habit)}
                  </small>
                {/if}
              </span>
              <small class="habits__correlation">{correlationListLabel(row.habit)}</small>
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
  .habits__window {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .habits__window {
    margin-top: var(--space-1);
    font-size: var(--text-xs);
    font-weight: 600;
  }
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
    min-height: 6.25rem;
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
  .habits__row-body {
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
  .habits__row-body small {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .habits__row-body {
    font-variant-numeric: tabular-nums;
    width: min(19rem, 52%);
    min-width: 12rem;
  }

  .habits__goal,
  .habits__row-meta,
  .habits__trend {
    display: flex;
    align-items: center;
  }

  .habits__goal,
  .habits__row-meta {
    justify-content: space-between;
    gap: var(--space-2);
  }

  .habits__goal span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .habits__goal strong {
    font-size: var(--text-sm);
    line-height: 1;
  }

  .habits__row-bar {
    display: block;
    height: 0.45rem;
    overflow: hidden;
    border-radius: var(--radius-full);
    background: oklch(from var(--color-text) l c h / 0.08);
  }

  .habits__row-bar span {
    display: block;
    width: var(--habit-progress);
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
  }

  .habits__trend {
    gap: 0.2rem;
    white-space: nowrap;
  }

  .habits__trend--up,
  .habits__trend--flat {
    color: var(--color-text-muted);
  }

  .habits__trend--down {
    color: var(--color-warning);
  }

  .habits__correlation {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .habits__empty {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    padding: var(--space-3);
  }

  .habits__empty-lead {
    margin: 0;
  }

  .habits__setup {
    display: grid;
    gap: var(--space-3);
  }

  .habits__setup label {
    display: grid;
    gap: var(--space-1);
    font-size: var(--text-sm);
  }

  .habits__setup label span {
    color: var(--color-text-muted);
  }

  @media (max-width: 760px) {
    .habits__header,
    .habits__empty {
      align-items: stretch;
      flex-direction: column;
    }

    .habits__list button {
      align-items: stretch;
      flex-direction: column;
    }

    .habits__row-body {
      width: 100%;
      min-width: 0;
    }
  }
</style>
