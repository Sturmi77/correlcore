<script context="module" lang="ts">
  export type MetricCardMetric =
    | 'mood_score'
    | 'energy'
    | 'stress'
    | 'tracking_consistency'
    | 'count';
</script>

<script lang="ts">
  export let metric: MetricCardMetric;
  export let label: string;
  export let value: string;
  export let unit = '';
  export let loading = false;
</script>

<div class="metric-card" data-metric={metric} data-loading={loading ? 'true' : 'false'}>
  <dt class="metric-card__label">{label}</dt>
  <dd class="metric-card__value">
    {value}
    {#if unit}<span class="metric-card__unit">{unit}</span>{/if}
  </dd>
</div>

<style>
  .metric-card {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.6rem 0.7rem;
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .metric-card__label {
    margin: 0;
    font-size: var(--text-2xs);
    opacity: 0.7;
  }

  .metric-card__value {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .metric-card__unit {
    font-size: var(--text-2xs);
    font-weight: 400;
    opacity: 0.55;
  }

  .metric-card[data-loading='true'] .metric-card__value {
    opacity: 0.4;
  }
</style>
