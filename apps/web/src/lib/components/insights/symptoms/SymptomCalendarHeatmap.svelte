<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturityPhase } from '$lib/api/insights';
  import type { SymptomHeatmapSymptom } from '$lib/api/stats';
  import {
    buildSymptomCalendarGrid,
    symptomOccurrenceCount,
    symptomPresenceByDate,
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

  <div
    class="symptom-calendar__grid-wrap"
    data-scrollable={cells.length / 7 > 8 ? 'true' : 'false'}
  >
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
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    min-width: 0;
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
    border-radius: 2px;
    flex-shrink: 0;
  }

  .symptom-calendar__swatch--absent {
    background: var(--color-surface-offset);
  }

  .symptom-calendar__swatch--present {
    background: var(--color-warning);
  }

  .symptom-calendar__cell {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: none;
    padding: 0;
    background: var(--color-surface-offset);
    cursor: pointer;
  }

  .symptom-calendar__cell--present {
    background: var(--color-warning);
  }

  .symptom-calendar__cell--pad {
    background: transparent;
    pointer-events: none;
  }

  .symptom-calendar__cell:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  @media (max-width: 420px) {
    .symptom-calendar__grid {
      grid-template-rows: repeat(7, 10px);
      grid-auto-columns: 10px;
    }

    .symptom-calendar__cell {
      width: 10px;
      height: 10px;
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
