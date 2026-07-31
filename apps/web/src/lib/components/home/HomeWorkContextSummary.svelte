<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { WorkContextSummaryItem } from '$lib/api/dashboard';
  import {
    buildWorkContextDisplayItems,
    workContextMetricBarWidth,
    workContextMetricHighLow,
    workContextMetricNeutralBarColor,
    type WorkContextMetricKey,
  } from '$lib/utils/homeWorkContextSummary';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';

  export let workContextSummary: WorkContextSummaryItem[] = [];
  export let loading = false;

  let workContextMetric: WorkContextMetricKey = 'mood';

  $: workContextMetricOptions = [
    { id: 'mood', label: $_('home.brief.metric_mood'), testId: 'home-work-context-metric-mood' },
    {
      id: 'energy',
      label: $_('home.brief.metric_energy'),
      testId: 'home-work-context-metric-energy',
    },
    {
      id: 'stress',
      label: $_('home.brief.metric_stress'),
      testId: 'home-work-context-metric-stress',
    },
  ] satisfies SegmentedControlOption[];

  function formatAverage(value: number | null): string {
    return value === null ? $_('home.brief.none') : value.toFixed(1);
  }

  $: visibleWorkContexts = buildWorkContextDisplayItems(workContextSummary, workContextMetric);
  $: workContextMetricValues = visibleWorkContexts
    .map((item) => item.metricAvg)
    .filter((value): value is number => value !== null);
  $: ({ high: maxWorkContextMetric, low: minWorkContextMetric } = workContextMetricHighLow(
    workContextMetricValues,
    workContextMetric
  ));
  $: workContextBarColor = workContextMetricNeutralBarColor(workContextMetric);
</script>

{#if visibleWorkContexts.length || loading}
  <section
    class="work-context-summary"
    data-testid="home-work-context-summary"
    data-metric={workContextMetric}
    aria-busy={loading}
    aria-label={$_('home.brief.work_context_heading')}
  >
    <div class="work-context-summary__header">
      <h3>{$_('home.brief.work_context_heading')}</h3>
      <span>{$_('home.brief.work_context_hint')}</span>
    </div>
    <SegmentedControl
      value={workContextMetric}
      options={workContextMetricOptions}
      ariaLabel={$_('home.brief.work_context_metric_aria')}
      testId="home-work-context-metric-switcher"
      equalWidth={false}
      on:change={({ detail }) => {
        workContextMetric = detail.value as WorkContextMetricKey;
      }}
    />
    <div class="work-context-summary__list">
      {#each visibleWorkContexts as item}
        <div
          class="work-context-summary__row"
          data-highlight={item.metricAvg !== null &&
          maxWorkContextMetric !== null &&
          item.metricAvg === maxWorkContextMetric
            ? 'high'
            : item.metricAvg !== null &&
                minWorkContextMetric !== null &&
                item.metricAvg === minWorkContextMetric
              ? 'low'
              : 'none'}
        >
          <span>{$_(`entry.work_context.${item.work_context}`)}</span>
          <div
            class="work-context-summary__bar"
            aria-hidden="true"
            style={`--bar-width: ${workContextMetricBarWidth(workContextMetric, item.metricAvg)}; --bar-metric-color: ${workContextBarColor}`}
          ></div>
          <strong>
            {$_('home.brief.work_context_value', {
              values: {
                count: item.entry_count,
                mood: formatAverage(item.metricAvg),
              },
            })}
          </strong>
        </div>
      {/each}
    </div>
  </section>
{/if}

<style>
  .work-context-summary {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-5);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .work-context-summary__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: baseline;
  }

  .work-context-summary__header h3 {
    margin: 0;
    font-size: var(--text-sm);
  }

  .work-context-summary__header span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .work-context-summary__list {
    display: grid;
    gap: var(--space-2);
  }

  .work-context-summary__row {
    display: grid;
    grid-template-columns: minmax(6rem, 0.9fr) minmax(5rem, 1.4fr) minmax(5rem, auto);
    gap: var(--space-2);
    align-items: center;
    font-size: var(--text-sm);
  }

  .work-context-summary__row > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .work-context-summary__row strong {
    justify-self: end;
    white-space: nowrap;
  }

  .work-context-summary__bar {
    min-width: 0;
    height: 0.55rem;
    border-radius: var(--radius-full);
    background:
      linear-gradient(
          var(--bar-color, var(--bar-metric-color, var(--color-primary))),
          var(--bar-color, var(--bar-metric-color, var(--color-primary)))
        )
        left center / var(--bar-width) 100% no-repeat,
      var(--color-surface);
  }

  .work-context-summary__row[data-highlight='high'] .work-context-summary__bar {
    --bar-color: var(--color-success, var(--color-primary));
  }

  .work-context-summary__row[data-highlight='low'] .work-context-summary__bar {
    --bar-color: var(--color-warning, var(--color-primary));
  }

  .work-context-summary[data-metric='stress']
    .work-context-summary__row[data-highlight='low']
    .work-context-summary__bar {
    --bar-color: var(--color-metric-stress, var(--color-primary));
  }

  @media (max-width: 480px) {
    .work-context-summary__header {
      flex-direction: column;
      gap: var(--space-1);
    }

    .work-context-summary__row {
      grid-template-columns: 1fr;
    }

    .work-context-summary__row strong {
      justify-self: start;
    }
  }
</style>
