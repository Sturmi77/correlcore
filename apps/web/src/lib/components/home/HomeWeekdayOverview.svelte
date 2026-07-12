<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import {
    buildWeekdayOverviewCells,
    hasWeekdayOverviewContent,
  } from '$lib/utils/homeWeekdayOverview';
  export let insights: InsightResponse[] = [];
  export let weekdayInsight: InsightResponse | null = null;

  $: cells = buildWeekdayOverviewCells(weekdayInsight ? [weekdayInsight, ...insights] : insights);
  $: knownMood = cells
    .map((cell) => cell.moodAvg)
    .filter((value): value is number => value !== null);
  $: maxMood = Math.max(5, ...(knownMood.length ? knownMood : [5]));
  $: minMood = knownMood.length ? Math.min(...knownMood) : null;
  $: showOverview = hasWeekdayOverviewContent(cells);
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

    <div class="weekday-overview__chart" role="img" aria-label={$_('home.weekday_overview.aria')}>
      {#each cells as cell (cell.weekday)}
        <div
          class="weekday-overview__cell"
          data-highlight={cell.moodAvg !== null && cell.moodAvg === maxMood
            ? 'high'
            : cell.moodAvg !== null && minMood !== null && cell.moodAvg === minMood
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
            <span class="weekday-overview__finding" data-type={cell.findingType ?? 'context'}>
              {cell.findingLabel}
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
      <p class="weekday-overview__statement">{weekdayInsight.statement}</p>
    {/if}
    <p class="weekday-overview__hint">{$_('home.weekday_overview.hint')}</p>
  </section>
{:else}
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
    border-radius: 999px;
    padding: 0.18rem 0.55rem;
    font-size: 0.68rem;
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
    border-radius: 0.45rem;
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
    font-size: 0.68rem;
    color: var(--color-text-muted);
  }

  .weekday-overview__finding {
    font-size: 0.62rem;
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

  .weekday-overview__finding--empty {
    color: var(--color-text-muted);
    opacity: 0.7;
  }

  .weekday-overview__bar {
    width: 100%;
    max-width: 1.2rem;
    min-height: 0.25rem;
    border-radius: 999px 999px 0.25rem 0.25rem;
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
    border-radius: 0.45rem;
  }

  .weekday-overview__hint {
    color: var(--color-text-muted);
    font-size: 0.72rem;
  }
</style>
