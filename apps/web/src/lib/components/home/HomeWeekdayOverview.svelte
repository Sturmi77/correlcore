<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import type { WeekdaySummaryItem } from '$lib/api/dashboard';
  import { stripLegacyInsightStatementTails } from '$lib/utils/stripLegacyInsightStatementTails';
  import {
    buildWeekdayOverviewCells,
    hasWeekdayOverviewContent,
  } from '$lib/utils/homeWeekdayOverview';
  export let insights: InsightResponse[] = [];
  export let weekdayInsight: InsightResponse | null = null;
  export let weekdaySummary: WeekdaySummaryItem[] = [];
  /** While true, suppress the empty state — insights haven't finished loading
   * (or failed to load) yet, so "no weekday pattern yet" would be premature. */
  export let loading = false;

  $: cells = buildWeekdayOverviewCells(
    weekdayInsight ? [weekdayInsight, ...insights] : insights,
    weekdaySummary
  );
  $: knownMood = cells
    .map((cell) => cell.moodAvg)
    .filter((value): value is number => value !== null);
  /** Bar-height scale: clamped to the 1–5 mood range so bars stay proportional. */
  $: maxMood = Math.max(5, ...(knownMood.length ? knownMood : [5]));
  /** Highlight bounds: actual best/worst day. Comparing against the clamped
   * scale max instead would mean the best day is never marked unless its
   * average is exactly 5.0 (found via mock-data browser audit). */
  $: highMood = knownMood.length ? Math.max(...knownMood) : null;
  $: minMood = knownMood.length ? Math.min(...knownMood) : null;
  $: showOverview = hasWeekdayOverviewContent(cells);

  /** Resolve the label, translating the work_context enum but not user data. */
  function labelFor(cell: (typeof cells)[number]): string {
    if (cell.findingLabelKey) {
      const translated = $_(cell.findingLabelKey);
      return translated === cell.findingLabelKey ? (cell.findingLabel ?? '') : translated;
    }
    return cell.findingLabel ?? '';
  }

  /**
   * The chart is `role="img"`, whose descendants are presented as one atomic
   * image — per-cell text inside it is never announced. The findings therefore
   * have to live in the chart's own accessible name (#487 review).
   */
  $: chartLabel = [
    $_('home.weekday_overview.aria'),
    ...cells
      .filter((cell) => cell.findingLabel)
      .map(
        (cell) =>
          `${$_(`home.weekday.${cell.weekday}`)} — ${$_(
            cell.findingSource === 'confounder'
              ? 'home.weekday_overview.finding_confounder'
              : 'home.weekday_overview.finding_top_signal'
          )}${labelFor(cell)}`
      ),
  ].join('. ');
</script>

{#if showOverview}
  <section
    class="weekday-overview"
    data-testid="home-weekday-overview"
    aria-label={$_('home.weekday_overview.heading')}
  >
    <header class="weekday-overview__header">
      <h2 class="weekday-overview__heading">{$_('home.weekday_overview.heading')}</h2>
      {#if weekdayInsight}
        <span class="weekday-overview__tier">{$_('home.weekday_pattern.early_signal')}</span>
      {/if}
    </header>

    <div class="weekday-overview__chart" role="img" aria-label={chartLabel}>
      {#each cells as cell (cell.weekday)}
        <div
          class="weekday-overview__cell"
          data-highlight={highMood === minMood || cell.moodAvg === null
            ? 'none'
            : cell.moodAvg === highMood
              ? 'high'
              : cell.moodAvg === minMood
                ? 'low'
                : 'none'}
        >
          <span class="weekday-overview__value">
            {cell.moodAvg === null ? '-' : cell.moodAvg.toFixed(1)}
          </span>
          <span
            class="weekday-overview__bar"
            style={`height: ${cell.moodAvg === null ? 4 : Math.max(8, (cell.moodAvg / maxMood) * 56)}px`}
          ></span>
          {#if cell.findingLabel}
            <span
              class="weekday-overview__finding"
              data-type={cell.findingType ?? 'context'}
              data-source={cell.findingSource ?? 'top_signal'}
            >
              {labelFor(cell)}
            </span>
          {:else}
            <span class="weekday-overview__finding weekday-overview__finding--empty">
              {$_('home.weekday_overview.no_finding')}
            </span>
          {/if}
          <span class="weekday-overview__label">{$_(`home.weekday.${cell.weekday}`)}</span>
        </div>
      {/each}
    </div>

    {#if weekdayInsight?.statement}
      <p class="weekday-overview__statement">
        {stripLegacyInsightStatementTails(weekdayInsight.statement)}
      </p>
    {/if}
    <p class="weekday-overview__hint">{$_('home.weekday_overview.hint')}</p>
  </section>
{:else if !loading}
  <section
    class="weekday-overview weekday-overview--empty"
    data-testid="home-weekday-overview-empty"
    aria-label={$_('home.weekday_overview.heading')}
  >
    <h2 class="weekday-overview__heading">{$_('home.weekday_overview.heading')}</h2>
    <p class="weekday-overview__empty">{$_('home.weekday_overview.empty')}</p>
    <p class="weekday-overview__hint">{$_('home.weekday_overview.empty_hint')}</p>
  </section>
{/if}

<style>
  .weekday-overview {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .weekday-overview__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .weekday-overview__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    margin: 0;
  }

  .weekday-overview__tier {
    border-radius: var(--radius-full);
    padding: 0.18rem 0.55rem;
    font-size: var(--text-2xs);
    font-weight: 600;
    background: color-mix(in srgb, var(--color-primary) 10%, transparent);
    color: var(--color-primary);
  }

  .weekday-overview__chart {
    min-height: 8.5rem;
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    align-items: end;
    gap: 0.35rem;
    padding: 0.75rem 0.5rem 0.55rem;
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    border-radius: var(--radius-md);
  }

  .weekday-overview__cell {
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: end;
    gap: 0.2rem;
  }

  .weekday-overview__value,
  .weekday-overview__label {
    font-size: var(--text-2xs);
    color: var(--color-text-muted);
  }

  .weekday-overview__finding {
    font-size: var(--text-2xs);
    line-height: 1.2;
    text-align: center;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    max-width: 100%;
    min-height: 1.45rem;
  }

  .weekday-overview__finding[data-type='symptom'] {
    color: var(--color-primary);
  }

  /* #487: a confounder says "this looked real but dissolves once weekday
     effects are adjusted for" — a caveat. A top signal only says "this happens
     most often here". The caveat is rarer and stronger, so it gets weight and a
     dotted underline; the descriptive one stays quiet.

     The accent is a decoration colour, not a text colour: --color-warning is
     not in the contrast-validated token set, and text at --text-2xs has no
     headroom to spare. */
  .weekday-overview__finding[data-source='confounder'] {
    font-weight: 600;
    text-decoration: underline dotted from-font;
    text-decoration-color: var(--color-warning);
    text-underline-offset: 0.2em;
  }

  .weekday-overview__finding[data-source='top_signal'] {
    color: var(--color-text-muted);
  }

  .weekday-overview__finding--empty {
    color: var(--color-text-muted);
    opacity: 0.7;
  }

  .weekday-overview__bar {
    width: 100%;
    max-width: 1.2rem;
    min-height: 0.25rem;
    border-radius: var(--radius-full) var(--radius-full) var(--radius-sm) var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 45%, transparent);
  }

  .weekday-overview__cell[data-highlight='high'] .weekday-overview__bar {
    background: var(--color-success);
  }

  .weekday-overview__cell[data-highlight='low'] .weekday-overview__bar {
    background: var(--color-warning);
  }

  .weekday-overview__statement,
  .weekday-overview__hint,
  .weekday-overview__empty {
    margin: 0;
    font-size: var(--text-sm, 0.88rem);
    line-height: 1.45;
  }

  .weekday-overview--empty {
    padding: 0.75rem 0.5rem;
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    border-radius: var(--radius-md);
  }

  .weekday-overview__hint {
    color: var(--color-text-muted);
    font-size: var(--text-2xs);
  }
</style>
