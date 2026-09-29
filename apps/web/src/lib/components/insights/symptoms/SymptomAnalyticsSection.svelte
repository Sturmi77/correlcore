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
  import { compareDailyAxisLayoutFromRoot } from '$lib/utils/trendsDateAxis';
  import ComparisonHeatmap from '$lib/components/trends/ComparisonHeatmap.svelte';
  import { buildIsoDateRange } from '$lib/utils/charts';
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
  export let cooccurrenceError = false;
  export let phase: InsightMaturityPhase | null = null;
  export let loading = false;
  export let pruneSparseAxes = true;

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    selectCell: { cell: SymptomTagCooccurrenceCell };
  }>();

  let showAllCalendars = false;
  let showAllTrends = false;
  let cooccurrenceSortMode: 'alphabetical' | 'clustered' = 'alphabetical';
  let axisLayout = compareDailyAxisLayoutFromRoot(16);

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
