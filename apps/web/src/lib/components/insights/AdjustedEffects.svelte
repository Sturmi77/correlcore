<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { parseAdjustedEffects, type AdjustedValue } from '$lib/utils/adjustedEffects';

  export let insight: InsightResponse;

  $: view = parseAdjustedEffects(insight);

  function display(value: AdjustedValue): string {
    if (value.state === 'measured') return value.value.toFixed(3);
    return $_(`insights.signal.adjusted_${value.state}`);
  }
</script>

<details class="adjusted" data-testid="adjusted-effects">
  <summary data-testid="adjusted-effects-toggle">{$_('insights.signal.adjusted_heading')}</summary>
  {#if view}
    <p>{$_('insights.signal.adjusted_explanation')}</p>
    <dl>
      <div>
        <dt>{$_('insights.signal.adjusted_raw_r')}</dt>
        <dd data-testid="adjusted-raw-r">
          {view.rawCorrelation === null
            ? $_('insights.signal.adjusted_not_calculated')
            : view.rawCorrelation.toFixed(3)}
        </dd>
      </div>
      <div>
        <dt>{$_('insights.signal.adjusted_raw_difference')}</dt>
        <dd data-testid="adjusted-raw-difference">
          {view.rawMeanDifference === null
            ? $_('insights.signal.adjusted_not_calculated')
            : view.rawMeanDifference.toFixed(3)}
        </dd>
      </div>
      <div>
        <dt>{$_('insights.signal.adjusted_weekday')}</dt>
        <dd data-testid="adjusted-weekday">{display(view.weekday)}</dd>
      </div>
      <div>
        <dt>{$_('insights.signal.adjusted_calendar')}</dt>
        <dd data-testid="adjusted-calendar">{display(view.calendar)}</dd>
      </div>
    </dl>
    <p>{$_('insights.signal.adjusted_units')}</p>
  {:else}
    <p data-testid="adjusted-unsupported">{$_('insights.signal.adjusted_unsupported')}</p>
  {/if}
</details>

<style>
  .adjusted {
    border-top: 1px solid var(--color-border);
    padding-top: var(--space-2);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }
  .adjusted summary {
    cursor: pointer;
    color: var(--color-text);
    font-weight: 600;
  }
  .adjusted summary:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
  .adjusted dl {
    margin: var(--space-2) 0;
    display: grid;
    gap: var(--space-1);
  }
  .adjusted dl > div {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
  }
  .adjusted dd {
    margin: 0;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
</style>
