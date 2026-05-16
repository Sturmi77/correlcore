<script lang="ts">
  /**
   * InsightQualityMeter — Issue #184, FRONTEND.md §6.4.
   *
   * Descriptive progress toward first insight (30 day entries).
   * No imperatives, urgency, or emoji.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightTier } from '$lib/api/insights';
  import { estimateInsightReadiness } from '$lib/utils/insightQuality';

  export let dayEntryDates: readonly string[] = [];
  export let insightTier: InsightTier = 'none';
  export let confidenceScore = 0;
  export let loading = false;
  export let asOfIso: string | undefined = undefined;

  function confidenceLabel(score: number): string {
    if (score < 0.2) return 'early_signal';
    if (score < 0.4) return 'emerging_pattern';
    if (score < 0.6) return 'moderate_finding';
    if (score < 0.8) return 'strong_finding';
    return 'very_strong_finding';
  }

  $: estimate = estimateInsightReadiness({ dayEntryDates, asOfIso });
  $: fillPercent = Math.round(estimate.progressRatio * 100);
  $: clampedConfidence = Math.min(1, Math.max(0, confidenceScore));
  $: confidenceLabelKey = confidenceLabel(clampedConfidence);

  function bodyKey(stage: typeof estimate.stage): string {
    switch (stage) {
      case 'getting_started':
        return 'insights.quality_meter.getting_started';
      case 'building_with_pace':
        return 'insights.quality_meter.building_pace';
      case 'building_no_recent':
        return 'insights.quality_meter.building_no_recent';
      case 'ready_low':
        return 'insights.quality_meter.ready_low';
      case 'ready_full':
        return 'insights.quality_meter.ready_full';
    }
  }

  $: bodyValues =
    estimate.stage === 'building_with_pace'
      ? {
          current: estimate.totalEntryCount,
          target: estimate.targetEntries,
          weeks: estimate.estimatedWeeks ?? 1,
        }
      : estimate.showProgressFraction
        ? { current: estimate.totalEntryCount, target: estimate.targetEntries }
        : {};
</script>

<section
  class="insight-quality"
  data-testid="insight-quality-meter"
  data-stage={estimate.stage}
  data-tier={insightTier}
  data-loading={loading ? 'true' : 'false'}
  aria-busy={loading}
>
  <header class="insight-quality__header">
    <h2 class="insight-quality__heading">
      {$_('insights.quality_meter.heading')}
    </h2>
    {#if estimate.showProgressFraction}
      <span class="insight-quality__fraction" data-testid="insight-quality-fraction">
        {estimate.totalEntryCount}/{estimate.targetEntries}
      </span>
    {/if}
  </header>

  <div
    class="insight-quality__track"
    role="meter"
    aria-valuenow={estimate.progressRatio}
    aria-valuemin={0}
    aria-valuemax={1}
    aria-label={$_('insights.quality_meter.heading')}
    data-testid="insight-quality-track"
  >
    <span
      class="insight-quality__fill"
      data-testid="insight-quality-fill"
      style={`width: ${fillPercent}%`}
    ></span>
  </div>

  <p class="insight-quality__body" data-testid="insight-quality-body">
    {#if estimate.stage === 'ready_low' && clampedConfidence > 0}
      <span class="insight-quality__confidence" data-testid="insight-quality-confidence-label">
        {$_(`insights.confidence_label.${confidenceLabelKey}`)}
      </span>
      <span class="insight-quality__body-sep" aria-hidden="true"> · </span>
    {/if}
    {$_(bodyKey(estimate.stage), { values: bodyValues })}
  </p>

  {#if estimate.stage === 'ready_low' || estimate.stage === 'ready_full'}
    <p class="insight-quality__meta" data-testid="insight-quality-meta">
      {$_('insights.quality_meter.entry_total', { values: { n: estimate.totalEntryCount } })}
    </p>
  {/if}
</section>

<style>
  .insight-quality {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: var(--space-4);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    border-radius: var(--radius-lg);
    background: var(--color-surface);
  }

  .insight-quality__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .insight-quality__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    margin: 0;
  }

  .insight-quality__fraction {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--color-text-muted);
  }

  .insight-quality__track {
    position: relative;
    width: 100%;
    height: 0.55rem;
    overflow: hidden;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-border) 55%, transparent);
  }

  .insight-quality__fill {
    display: block;
    height: 100%;
    border-radius: inherit;
    transition: width 220ms ease;
    background: var(--color-primary);
  }

  .insight-quality__body {
    font-size: 0.85rem;
    line-height: 1.45;
    margin: 0;
    color: var(--color-text);
  }

  .insight-quality__confidence {
    font-weight: 600;
  }

  .insight-quality__meta {
    font-size: 0.72rem;
    color: var(--color-text-muted);
    margin: 0;
  }

  .insight-quality[data-loading='true'] {
    opacity: 0.7;
  }

  @media (prefers-reduced-motion: reduce) {
    .insight-quality__fill {
      transition: none;
    }
  }
</style>
