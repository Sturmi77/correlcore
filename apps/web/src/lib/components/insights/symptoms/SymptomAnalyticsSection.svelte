<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import type {
    InsightMaturityPhase,
    SymptomTagCooccurrenceCell,
    SymptomTagCooccurrenceResponse,
  } from '$lib/api/insights';
  import type { SymptomHeatmapResponse } from '$lib/api/stats';
  import { onMount } from 'svelte';
  import ComparisonHeatmap from '$lib/components/trends/ComparisonHeatmap.svelte';
  import { buildIsoDateRange, compareDailyAxisLayout } from '$lib/utils/charts';
  import { compareDailyAxisLayoutFromRoot } from '$lib/utils/trendsDateAxis';
  import {
    SYMPTOM_CALENDAR_MAX_VISIBLE,
    SYMPTOM_TREND_MAX_VISIBLE,
    buildMoodByDate,
    buildSymptomTrendSeries,
    rankEligibleSymptoms,
    symptomPresenceByDate,
    trendDatesForHeatmap,
  } from '$lib/utils/symptomAnalyticsViews';
  import SymptomCalendarHeatmap from './SymptomCalendarHeatmap.svelte';
  import SymptomCooccurrenceHeatmap from './SymptomCooccurrenceHeatmap.svelte';
  import SymptomTrendOverlay from './SymptomTrendOverlay.svelte';
  import { canShowSymptomCooccurrence } from '$lib/utils/insightAnalyticsGate';

  export let heatmap: SymptomHeatmapResponse | null = null;
  export let entries: EntryResponse[] = [];
  export let cooccurrence: SymptomTagCooccurrenceResponse | null = null;
  export let cooccurrenceLoading = false;
  export let phase: InsightMaturityPhase | null = null;
  export let loading = false;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    selectCell: { cell: SymptomTagCooccurrenceCell };
  }>();

  let showAllCalendars = false;
  let showAllTrends = false;
  let cooccurrenceSortMode: 'alphabetical' | 'clustered' = 'alphabetical';
  let axisLayout = compareDailyAxisLayout;

  onMount(() => {
    const rootPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    axisLayout = compareDailyAxisLayoutFromRoot(rootPx);
  });

  $: dates = heatmap ? buildIsoDateRange(heatmap.start_date, heatmap.end_date) : [];
  $: eligibleSymptoms = heatmap ? rankEligibleSymptoms(heatmap.symptoms) : [];
  $: visibleCalendars = showAllCalendars
    ? eligibleSymptoms
    : eligibleSymptoms.slice(0, SYMPTOM_CALENDAR_MAX_VISIBLE);
  $: visibleTrendSymptoms = showAllTrends
    ? eligibleSymptoms
    : eligibleSymptoms.slice(0, SYMPTOM_TREND_MAX_VISIBLE);
  $: moodByDate = buildMoodByDate(entries);
  $: trendDates = heatmap ? trendDatesForHeatmap(heatmap.start_date, heatmap.end_date) : [];
  $: showCooccurrencePanel =
    canShowSymptomCooccurrence(phase) &&
    (cooccurrenceLoading || (cooccurrence?.cells.length ?? 0) > 0);
</script>

<section class="symptom-analytics" aria-labelledby="symptom-analytics-heading">
  <header class="symptom-analytics__header">
    <div>
      <h2 id="symptom-analytics-heading">{$_('insights.symptoms.heading')}</h2>
      <p>{$_('insights.symptoms.body')}</p>
    </div>
  </header>

  <ComparisonHeatmap
    tagHeatmap={null}
    symptomHeatmap={heatmap}
    showTags={false}
    showSymptoms={true}
    {loading}
    {dates}
    {axisLayout}
    headingKey="insights.symptoms.heatmap_heading"
    emptyKey="insights.symptoms.empty"
    on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
  />

  {#if heatmap && visibleCalendars.length > 0}
    <section class="symptom-analytics__subsection" aria-labelledby="symptom-calendar-heading">
      <header class="symptom-analytics__subheader">
        <h3 id="symptom-calendar-heading">{$_('insights.symptoms.calendar_heading')}</h3>
        {#if eligibleSymptoms.length > SYMPTOM_CALENDAR_MAX_VISIBLE}
          <button
            type="button"
            class="symptom-analytics__toggle"
            on:click={() => (showAllCalendars = !showAllCalendars)}
          >
            {showAllCalendars
              ? $_('insights.symptoms.show_fewer')
              : $_('insights.symptoms.show_all_calendars')}
          </button>
        {/if}
      </header>
      <div class="symptom-analytics__stack">
        {#each visibleCalendars as symptom (symptom.symptom_id)}
          <SymptomCalendarHeatmap
            {symptom}
            startDate={heatmap.start_date}
            endDate={heatmap.end_date}
            {phase}
            on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
          />
        {/each}
      </div>
    </section>
  {/if}

  {#if heatmap && visibleTrendSymptoms.length > 0}
    <section class="symptom-analytics__subsection" aria-labelledby="symptom-trend-heading">
      <header class="symptom-analytics__subheader">
        <h3 id="symptom-trend-heading">{$_('insights.symptoms.trend_heading')}</h3>
        {#if eligibleSymptoms.length > SYMPTOM_TREND_MAX_VISIBLE}
          <button
            type="button"
            class="symptom-analytics__toggle"
            on:click={() => (showAllTrends = !showAllTrends)}
          >
            {showAllTrends
              ? $_('insights.symptoms.show_fewer')
              : $_('insights.symptoms.show_all_trends')}
          </button>
        {/if}
      </header>
      <div class="symptom-analytics__stack">
        {#each visibleTrendSymptoms as symptom (symptom.symptom_id)}
          <SymptomTrendOverlay
            symptomName={symptom.name}
            data={buildSymptomTrendSeries(trendDates, symptomPresenceByDate(symptom), moodByDate)}
            {phase}
          />
        {/each}
      </div>
    </section>
  {/if}

  {#if showCooccurrencePanel}
    <section class="symptom-analytics__subsection" aria-labelledby="symptom-cooccurrence-heading">
      <header class="symptom-analytics__subheader">
        <h3 id="symptom-cooccurrence-heading">{$_('insights.symptoms.cooccurrence_heading')}</h3>
        {#if phase === 'robust'}
          <button
            type="button"
            class="symptom-analytics__toggle"
            on:click={() =>
              (cooccurrenceSortMode =
                cooccurrenceSortMode === 'alphabetical' ? 'clustered' : 'alphabetical')}
          >
            {cooccurrenceSortMode === 'clustered'
              ? $_('insights.symptoms.cooccurrence_sort_alphabetical')
              : $_('insights.symptoms.cooccurrence_sort_clustered')}
          </button>
        {/if}
      </header>
      <SymptomCooccurrenceHeatmap
        data={cooccurrence}
        loading={cooccurrenceLoading}
        {phase}
        sortMode={cooccurrenceSortMode}
        hideHeading={true}
        on:selectCell={(event) => dispatch('selectCell', event.detail)}
      />
    </section>
  {/if}
</section>

<style>
  .symptom-analytics {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    min-width: 0;
  }

  .symptom-analytics__header,
  .symptom-analytics__subheader {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: baseline;
  }

  .symptom-analytics__header h2,
  .symptom-analytics__header p,
  .symptom-analytics__subheader h3 {
    margin: 0;
  }

  .symptom-analytics__header h2 {
    font-size: var(--text-lg);
  }

  .symptom-analytics__header p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-analytics__subsection {
    display: grid;
    gap: var(--space-3);
  }

  .symptom-analytics__stack {
    display: grid;
    gap: var(--space-3);
  }

  .symptom-analytics__toggle {
    border: none;
    background: none;
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 600;
    cursor: pointer;
    padding: 0;
  }

  .symptom-analytics__toggle:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  @media (max-width: 520px) {
    .symptom-analytics {
      padding: var(--space-3);
      gap: var(--space-3);
    }

    .symptom-analytics__subheader {
      flex-wrap: wrap;
      align-items: center;
    }
  }
</style>
