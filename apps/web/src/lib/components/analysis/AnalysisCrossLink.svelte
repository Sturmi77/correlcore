<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import {
    INSIGHTS_TOP_FINDING_PATH,
    TRENDS_COMPARE_PATH,
    topInsightLabel,
  } from '$lib/utils/analysisCrossLinks';

  export let insight: InsightResponse;
  export let direction: 'to-insights' | 'to-trends' = 'to-insights';
</script>

<p class="analysis-cross-link" data-testid="analysis-cross-link">
  {#if direction === 'to-insights'}
    <a href={INSIGHTS_TOP_FINDING_PATH} data-testid="analysis-cross-link-insights">
      {$_('analysis.cross_link.top_insight', { values: { label: topInsightLabel(insight) } })}
    </a>
  {:else}
    <a href={TRENDS_COMPARE_PATH} data-testid="analysis-cross-link-trends">
      {$_('analysis.cross_link.view_trends')}
    </a>
  {/if}
</p>

<style>
  .analysis-cross-link {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.45;
  }

  .analysis-cross-link a {
    color: var(--color-primary);
    font-weight: 650;
    text-decoration: none;
  }

  .analysis-cross-link a:hover,
  .analysis-cross-link a:focus-visible {
    text-decoration: underline;
    text-underline-offset: 2px;
  }
</style>
