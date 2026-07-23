<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HabitStatsResponse } from '$lib/api/habits';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import type { TagResponse } from '$lib/api/tags';
  import TagHeatmap from '$lib/components/trends/TagHeatmap.svelte';
  import {
    formatHabitDelta,
    habitGoalI18nKey,
    habitMetricI18nKey,
    habitProgressValue,
    habitStatusI18nKey,
    isHabitAdherenceInsufficient,
  } from '$lib/utils/habitMetrics';

  export let selected: { habit: HabitStatsResponse; tag: TagResponse };
  export let detailHeatmap: TagHeatmapResponse | null = null;
  export let loading = false;

  const dispatch = createEventDispatcher<{ selectDate: { date: string; tagId: string } }>();

  function pct(value: number): string {
    return `${Math.round(value)}%`;
  }

  function metricLabel(metric: string | null | undefined): string {
    const key = habitMetricI18nKey(metric);
    if (!key) return '';
    const translated = $_(key);
    return translated === key ? (metric ?? '') : translated;
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
      return $_('habits.trend.unknown');
    }
    return $_('habits.trend.delta', {
      values: {
        delta: formatHabitDelta(habit.adherence_delta),
      },
    });
  }

  $: insufficient = isHabitAdherenceInsufficient(selected.habit);
  // #490: the visual difference between build and reduce is shape/texture, so
  // the meter has to name the type in text for screen readers.
  $: meterText = $_('habits.adherence_meter_text', {
    values: {
      type: $_(`habits.type.${selected.habit.habit_type}`),
      percent: pct(selected.habit.adherence_rate),
      goal: goalLabel(selected.habit),
    },
  });
</script>

<article class="habit-detail" data-testid="habit-detail">
  <div class="habit-detail__head">
    <div>
      <h3>{selected.tag.name}</h3>
      <p>{$_(`habits.type.${selected.habit.habit_type}`)}</p>
    </div>
    <strong>{pct(selected.habit.adherence_rate)}</strong>
  </div>

  {#if insufficient}
    <p class="habit-detail__muted" data-testid="habit-insufficient-data">
      {$_('habits.insufficient_data')}
    </p>
  {:else}
    <div
      class="habit-detail__bar"
      role="meter"
      data-habit-type={selected.habit.habit_type}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={selected.habit.adherence_rate}
      aria-label={$_('habits.adherence_meter')}
      aria-valuetext={meterText}
    >
      <span style={`width: ${habitProgressValue(selected.habit)}%`}></span>
    </div>

    <dl class="habit-detail__summary">
      <div>
        <dt>{$_('habits.status.label')}</dt>
        <dd>{$_(habitStatusI18nKey(selected.habit))}</dd>
      </div>
      <div>
        <dt>{$_('habits.goal.label')}</dt>
        <dd>{goalLabel(selected.habit)}</dd>
      </div>
      <div>
        <dt>{$_('habits.trend.label')}</dt>
        <dd>{trendLabel(selected.habit)}</dd>
      </div>
      <div>
        <dt>{$_('habits.period')}</dt>
        <dd>{selected.habit.start_date} - {selected.habit.end_date}</dd>
      </div>
    </dl>

    <dl class="habit-detail__stats">
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
      <section class="habit-detail__correlation">
        <p>
          {$_('habits.correlation_predictor', {
            values: {
              name: selected.tag.name,
              metric: metricLabel(selected.habit.correlation_metric),
              score: selected.habit.correlation_score.toFixed(2),
            },
          })}
        </p>
      </section>
    {/if}
  {/if}

  <TagHeatmap
    heatmap={detailHeatmap}
    {loading}
    compact
    on:selectDate={(event) => dispatch('selectDate', event.detail)}
  />
</article>

<style>
  .habit-detail {
    display: grid;
    gap: var(--space-4);
    min-width: 0;
  }

  .habit-detail__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .habit-detail h3,
  .habit-detail p {
    margin: 0;
  }

  .habit-detail__head > strong {
    font-size: var(--text-2xl);
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  .habit-detail__bar {
    height: 0.5rem;
    border-radius: var(--radius-full);
    background: oklch(from var(--color-text) l c h / 0.08);
    overflow: hidden;
  }

  .habit-detail__bar > span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
  }

  /* Mirrors HabitsPanel (#490): same value, different encoding — solid reads as
     progress toward a target, hatched as staying within a limit. */
  .habit-detail__bar[data-habit-type='reduce'] {
    box-shadow: inset 0 0 0 1px oklch(from var(--color-primary) l c h / 0.35);
    background: transparent;
  }

  .habit-detail__bar[data-habit-type='reduce'] > span {
    background: repeating-linear-gradient(
      135deg,
      var(--color-primary) 0,
      var(--color-primary) 2px,
      transparent 2px,
      transparent 5px
    );
  }

  .habit-detail__stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
    margin: 0;
  }

  .habit-detail__summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2);
    margin: 0;
  }

  .habit-detail__stats div,
  .habit-detail__summary div,
  .habit-detail__correlation {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    padding: var(--space-3);
  }

  .habit-detail__stats dt,
  .habit-detail__summary dt,
  .habit-detail__muted {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .habit-detail__stats dd,
  .habit-detail__summary dd {
    margin: 0.2rem 0 0;
    font-weight: 650;
  }

  .habit-detail__correlation p {
    margin: 0;
    font-size: var(--text-sm);
  }

  .habit-detail__muted {
    margin: 0;
    font-size: var(--text-sm);
  }

  @media (max-width: 767px) {
    .habit-detail__summary,
    .habit-detail__stats {
      grid-template-columns: 1fr;
    }
  }
</style>
