<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import type { InsightMaturityPhase } from '$lib/api/insights';
  import type { SymptomHeatmapSymptom } from '$lib/api/stats';
  import {
    buildSymptomCalendarGrid,
    symptomOccurrenceCount,
    symptomPresenceByDate,
    type SymptomCalendarCell,
  } from '$lib/utils/symptomAnalyticsViews';

  export let symptom: SymptomHeatmapSymptom;
  export let startDate: string;
  export let endDate: string;
  export let phase: InsightMaturityPhase | null = null;

  const dispatch = createEventDispatcher<{ selectDate: { date: string } }>();

  $: presenceByDate = symptomPresenceByDate(symptom);
  $: cells = buildSymptomCalendarGrid(startDate, endDate, presenceByDate);
  $: total = symptomOccurrenceCount(symptom);
  $: showCorrelationNote = phase === 'provisional' || phase === 'robust';

  // Axis labels so the grid is interpretable: weekday rows + month columns (#574).
  $: weekColumns = chunkWeeks(cells);
  $: weekdayLabels = buildWeekdayLabels($locale ?? 'de');
  $: monthLabels = buildMonthLabels(weekColumns, $locale ?? 'de');

  function chunkWeeks(gridCells: SymptomCalendarCell[]): SymptomCalendarCell[][] {
    const columns: SymptomCalendarCell[][] = [];
    for (let index = 0; index < gridCells.length; index += 7) {
      columns.push(gridCells.slice(index, index + 7));
    }
    return columns;
  }

  /** Monday-based rows; label Mon/Wed/Fri/Sun only to stay compact. */
  function buildWeekdayLabels(loc: string): string[] {
    const formatter = new Intl.DateTimeFormat(loc, { weekday: 'short' });
    const monday = new Date('2024-01-01T00:00:00'); // a Monday
    return Array.from({ length: 7 }, (_unused, row) => {
      if (row % 2 !== 0) return '';
      const day = new Date(monday);
      day.setDate(monday.getDate() + row);
      return formatter.format(day);
    });
  }

  /** One entry per week column: label when the ISO week starts a new month. */
  function buildMonthLabels(columns: SymptomCalendarCell[][], loc: string): string[] {
    const formatter = new Intl.DateTimeFormat(loc, { month: 'short' });
    let previous = '';
    return columns.map((week) => {
      const mondayCell = week[0];
      if (!mondayCell?.date) return '';
      const label = formatter.format(new Date(`${mondayCell.date}T00:00:00`));
      if (label === previous) return '';
      previous = label;
      return label;
    });
  }
</script>

<article class="symptom-calendar" aria-labelledby={`symptom-calendar-${symptom.symptom_id}`}>
  <header class="symptom-calendar__header">
    <h3 id={`symptom-calendar-${symptom.symptom_id}`}>
      {symptom.name}
    </h3>
    <p>
      {$_('insights.symptoms.calendar_occurrences', { values: { count: total } })}
    </p>
    {#if showCorrelationNote}
      <p class="symptom-calendar__note">{$_('insights.symptoms.calendar_correlation_note')}</p>
    {/if}
  </header>

  <div class="symptom-calendar__chart">
    <div class="symptom-calendar__weekdays" aria-hidden="true">
      {#each weekdayLabels as weekday}
        <span>{weekday}</span>
      {/each}
    </div>
    <div
      class="symptom-calendar__grid-wrap"
      data-scrollable={cells.length / 7 > 8 ? 'true' : 'false'}
    >
      <div class="symptom-calendar__months" aria-hidden="true">
        {#each monthLabels as month}
          <span class="symptom-calendar__month">{month}</span>
        {/each}
      </div>
      <div
        class="symptom-calendar__grid"
        role="grid"
        aria-label={$_('insights.symptoms.calendar_aria', { values: { name: symptom.name } })}
        style={`--week-count: ${cells.length / 7}`}
      >
        {#each cells as cell}
          {#if cell.date}
            <button
              type="button"
              class="symptom-calendar__cell"
              class:symptom-calendar__cell--present={cell.present}
              role="gridcell"
              aria-label={$_('insights.symptoms.calendar_cell_aria', {
                values: {
                  date: cell.date,
                  name: symptom.name,
                  state: cell.present
                    ? $_('insights.symptoms.calendar_present')
                    : $_('insights.symptoms.calendar_absent'),
                },
              })}
              title={$_('insights.symptoms.calendar_cell_aria', {
                values: {
                  date: cell.date,
                  name: symptom.name,
                  state: cell.present
                    ? $_('insights.symptoms.calendar_present')
                    : $_('insights.symptoms.calendar_absent'),
                },
              })}
              on:click={() => dispatch('selectDate', { date: cell.date! })}
            ></button>
          {:else}
            <span class="symptom-calendar__cell symptom-calendar__cell--pad" role="presentation"
            ></span>
          {/if}
        {/each}
      </div>
    </div>
  </div>

  <div class="symptom-calendar__legend" aria-label={$_('insights.symptoms.calendar_legend')}>
    <span class="symptom-calendar__legend-item">
      <span class="symptom-calendar__swatch symptom-calendar__swatch--absent" aria-hidden="true"
      ></span>
      {$_('insights.symptoms.calendar_absent')}
    </span>
    <span class="symptom-calendar__legend-item">
      <span class="symptom-calendar__swatch symptom-calendar__swatch--present" aria-hidden="true"
      ></span>
      {$_('insights.symptoms.calendar_present')}
    </span>
  </div>
  <p class="symptom-calendar__how-to-read">{$_('insights.symptoms.calendar_how_to_read')}</p>
</article>

<style>
  .symptom-calendar {
    --axis-month-row-h: 14px;
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    min-width: 0;
  }

  .symptom-calendar__chart {
    display: flex;
    gap: var(--space-1);
    min-width: 0;
    max-width: 100%;
  }

  .symptom-calendar__weekdays {
    flex-shrink: 0;
    display: grid;
    grid-template-rows: repeat(7, 12px);
    gap: var(--heatmap-calendar-gap);
    margin-top: var(--axis-month-row-h);
  }

  .symptom-calendar__weekdays span {
    display: flex;
    align-items: center;
    height: 12px;
    /* token-exempt: axis micro-label needs px precision at this size (F-10). */
    font-size: 9px;
    line-height: 1;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .symptom-calendar__months {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 12px;
    gap: var(--heatmap-calendar-gap);
    width: max-content;
    height: var(--axis-month-row-h);
  }

  .symptom-calendar__month {
    /* token-exempt: axis micro-label needs px precision at this size (F-10). */
    font-size: 9px;
    line-height: 1;
    color: var(--color-text-muted);
    white-space: nowrap;
    overflow: visible;
  }

  .symptom-calendar__header h3,
  .symptom-calendar__header p {
    margin: 0;
  }

  .symptom-calendar__header h3 {
    font-size: var(--text-base);
  }

  .symptom-calendar__header p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-calendar__note {
    margin-top: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .symptom-calendar__grid-wrap {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    max-width: 100%;
    min-width: 0;
    overflow-x: auto;
    padding-bottom: var(--space-1);
  }

  .symptom-calendar__grid-wrap[data-scrollable='true']::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1.5rem;
    height: 100%;
    pointer-events: none;
    background: linear-gradient(to left, var(--color-surface), transparent);
  }

  .symptom-calendar__grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(7, 12px);
    grid-auto-columns: 12px;
    gap: var(--heatmap-calendar-gap);
    width: max-content;
    max-width: none;
  }

  .symptom-calendar__legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .symptom-calendar__legend-item {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
  }

  .symptom-calendar__swatch {
    width: 12px;
    height: 12px;
    border-radius: var(--radius-sm); /* token-exempt: 2px micro-cell; sm is closest token */
    flex-shrink: 0;
  }

  .symptom-calendar__swatch--absent {
    background: var(--color-surface-offset);
  }

  .symptom-calendar__swatch--present {
    background: var(--color-heatmap-4);
  }

  .symptom-calendar__cell {
    position: relative;
    width: 12px;
    height: 12px;
    border-radius: var(--radius-sm); /* token-exempt: heatmap micro-cell */
    border: none;
    padding: 0;
    background: var(--color-surface-offset);
    cursor: pointer;
  }

  /* §1.6 dense-matrix exception: expand hit area to ≥24px without visual resize */
  .symptom-calendar__cell:not(.symptom-calendar__cell--pad)::after {
    content: '';
    position: absolute;
    inset: -6px;
  }

  .symptom-calendar__cell--present {
    background: var(--color-heatmap-4);
  }

  .symptom-calendar__cell--pad {
    background: transparent;
    pointer-events: none;
  }

  .symptom-calendar__cell:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  @media (max-width: 360px) {
    .symptom-calendar__grid {
      grid-template-rows: repeat(7, 10px);
      grid-auto-columns: 10px;
    }

    .symptom-calendar__weekdays {
      grid-template-rows: repeat(7, 10px);
    }

    .symptom-calendar__weekdays span {
      height: 10px;
      /* token-exempt: axis micro-label needs px precision at this size (F-10). */
      font-size: 8px;
    }

    .symptom-calendar__months {
      grid-auto-columns: 10px;
    }

    .symptom-calendar__cell {
      width: 10px;
      height: 10px;
    }

    .symptom-calendar__cell:not(.symptom-calendar__cell--pad)::after {
      inset: -7px;
    }
  }

  .symptom-calendar__how-to-read {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    line-height: 1.45;
    max-width: 36rem;
  }
</style>
