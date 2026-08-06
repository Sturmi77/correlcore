<script lang="ts">
  import Activity from 'lucide-svelte/icons/activity';
  import Minus from 'lucide-svelte/icons/minus';
  import Tag from 'lucide-svelte/icons/tag';
  import TrendingDown from 'lucide-svelte/icons/trending-down';
  import TrendingUp from 'lucide-svelte/icons/trending-up';
  import { _ } from 'svelte-i18n';
  import type {
    SymptomHeatmapResponse,
    TagHeatmapResponse,
    TimeseriesPoint,
    TimeseriesRange,
  } from '$lib/api/stats';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { buildMobileTrendsSummary } from '$lib/utils/mobileTrendsSummary';

  export let points: TimeseriesPoint[] = [];
  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let range: TimeseriesRange = 'week';
  export let loading = false;

  const metricLabels = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
    sleep_quality_avg: 'trends.metric.sleep_quality',
  } as const;

  function score(value: number): string {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value);
  }

  function delta(value: number): string {
    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 1,
      signDisplay: 'always',
    }).format(value);
  }

  $: summary = buildMobileTrendsSummary(points, tagHeatmap, symptomHeatmap);
</script>

<section
  class="mobile-summary"
  aria-labelledby="mobile-trends-summary-title"
  aria-busy={loading}
  data-testid="mobile-trends-summary"
>
  <header class="mobile-summary__header">
    <div>
      <span>{$_(`trends.range.${range}`)}</span>
      <h2 id="mobile-trends-summary-title">{$_('trends.mobile.heading')}</h2>
    </div>
    {#if loading}<small>{$_('trends.mobile.updating')}</small>{/if}
  </header>

  {#if summary.entryCount === 0 && !loading}
    <div class="mobile-summary__empty" data-testid="mobile-trends-summary-empty">
      <strong>{$_('trends.mobile.empty_heading')}</strong>
      <p>{$_('trends.mobile.empty_body')}</p>
    </div>
  {:else}
    <p class="mobile-summary__count">
      {$_('trends.mobile.entries', { values: { count: summary.entryCount } })}
    </p>
    <div class="mobile-summary__grid">
      <article class="mobile-summary__card mobile-summary__card--movement">
        <div class="mobile-summary__label">
          {#if summary.movement?.delta && summary.movement.delta > 0}
            <TrendingUp size={ICON_SIZE_MD} aria-hidden="true" />
          {:else if summary.movement?.delta && summary.movement.delta < 0}
            <TrendingDown size={ICON_SIZE_MD} aria-hidden="true" />
          {:else}
            <Minus size={ICON_SIZE_MD} aria-hidden="true" />
          {/if}
          <span>{$_('trends.mobile.movement')}</span>
        </div>
        {#if summary.movement}
          <strong>{$_(metricLabels[summary.movement.metric])}</strong>
          <p>
            {$_('trends.mobile.movement_value', {
              values: {
                from: score(summary.movement.from),
                to: score(summary.movement.to),
                delta: delta(summary.movement.delta),
              },
            })}
          </p>
        {:else}
          <strong>{$_('trends.mobile.not_enough')}</strong>
        {/if}
      </article>

      <article class="mobile-summary__card">
        <div class="mobile-summary__label">
          <Tag size={ICON_SIZE_MD} aria-hidden="true" /><span>{$_('trends.mobile.tag')}</span>
        </div>
        {#if summary.tag}
          <strong>{summary.tag.name}</strong>
          <p>
            {$_('trends.mobile.tag_value', {
              values: { count: summary.tag.occurrences, days: summary.tag.activeDays },
            })}
          </p>
        {:else}
          <strong>{$_('trends.mobile.no_tag')}</strong>
        {/if}
      </article>

      <article class="mobile-summary__card">
        <div class="mobile-summary__label">
          <Activity size={ICON_SIZE_MD} aria-hidden="true" /><span
            >{$_('trends.mobile.symptom')}</span
          >
        </div>
        {#if summary.symptom}
          <strong>{summary.symptom.name}</strong>
          <p>
            {$_('trends.mobile.symptom_value', {
              values: { count: summary.symptom.reports, peak: summary.symptom.peakIntensity },
            })}
          </p>
        {:else}
          <strong>{$_('trends.mobile.no_symptom')}</strong>
        {/if}
      </article>
    </div>
  {/if}
</section>

<style>
  .mobile-summary {
    display: grid;
    gap: var(--space-3);
  }

  .mobile-summary__header {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .mobile-summary__header span,
  .mobile-summary__header small,
  .mobile-summary__count,
  .mobile-summary__label,
  .mobile-summary__card p,
  .mobile-summary__empty p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .mobile-summary__header h2,
  .mobile-summary__count,
  .mobile-summary__card p,
  .mobile-summary__empty p {
    margin: 0;
  }

  .mobile-summary__header h2 {
    margin-top: var(--space-1);
    font-size: var(--text-xl);
  }

  .mobile-summary__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .mobile-summary__card,
  .mobile-summary__empty {
    min-width: 0;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .mobile-summary__card--movement {
    grid-column: 1 / -1;
  }

  .mobile-summary__card {
    display: grid;
    gap: var(--space-2);
  }

  .mobile-summary__card strong {
    overflow-wrap: anywhere;
    font-size: var(--text-lg);
  }

  .mobile-summary__label {
    display: flex;
    align-items: center;
    gap: var(--space-1);
  }

  .mobile-summary__label :global(svg) {
    flex: 0 0 auto;
    color: var(--color-primary);
  }

  .mobile-summary__empty {
    display: grid;
    gap: var(--space-1);
  }

  @media (max-width: 360px) {
    .mobile-summary__grid {
      grid-template-columns: 1fr;
    }

    .mobile-summary__card--movement {
      grid-column: auto;
    }
  }
</style>
