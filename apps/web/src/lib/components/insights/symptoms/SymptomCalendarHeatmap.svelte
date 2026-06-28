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
        <span class="symptom-calendar__cell symptom-calendar__cell--pad" role="presentation"></span>
      {/if}
    {/each}
  </div>
</article>

<style>
  .symptom-calendar {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
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

  .symptom-calendar__grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(7, 12px);
    grid-auto-columns: 12px;
    gap: 2px;
    overflow-x: auto;
    padding-bottom: var(--space-1);
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
</style>
