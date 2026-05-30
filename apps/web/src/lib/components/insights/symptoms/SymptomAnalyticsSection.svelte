<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { SymptomHeatmapResponse } from '$lib/api/stats';
  import ComparisonHeatmap from '$lib/components/trends/ComparisonHeatmap.svelte';
  import { buildIsoDateRange, compareDailyAxisLayout } from '$lib/utils/charts';

  export let heatmap: SymptomHeatmapResponse | null = null;
  export let loading = false;

  const dispatch = createEventDispatcher<{ selectDate: { date: string } }>();

  $: dates = heatmap ? buildIsoDateRange(heatmap.start_date, heatmap.end_date) : [];
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
    axisLayout={compareDailyAxisLayout}
    headingKey="insights.symptoms.heatmap_heading"
    emptyKey="insights.symptoms.empty"
    on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
  />
</section>

<style>
  .symptom-analytics {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .symptom-analytics__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .symptom-analytics__header h2,
  .symptom-analytics__header p {
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
</style>
