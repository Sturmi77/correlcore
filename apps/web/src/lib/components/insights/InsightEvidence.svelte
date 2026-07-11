<script lang="ts">
  /**
   * InsightEvidence — Sprint 2 consolidation (INSIGHT_STATEMENT_PATTERN_SPRINT_PLAN.md ISP-4).
   *
   * Single Level-2 evidence primitive, replacing InsightMaturityBadge and
   * InsightConfidenceScale (previously two components independently
   * expressing "how certain/mature is this"). One row: tier chip +
   * confidence dots (+ raw percent when `detailed`) + sample count.
   *
   * Props
   * -----
   * maturity          InsightMaturity | null — tier chip source
   * showMaturityBadge Hide the tier chip even when maturity is present
   * confidenceScore   Float 0–1. Clamped internally.
   * currentTier       InsightTier from the API (kept as a data attribute for styling/QA)
   * entryCount        Raw sample size
   * showSample        Show the "Based on N entries" line
   * detailed          Reveal the raw confidence percentage (Level 2 only)
   * loading           Dims the component while parent data is loading
   */
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightTier } from '$lib/api/insights';

  export let maturity: InsightMaturity | null = null;
  export let showMaturityBadge = true;
  export let confidenceScore = 0;
  export let currentTier: InsightTier = 'none';
  export let entryCount = 0;
  export let showConfidence = true;
  export let showSample = false;
  export let detailed = false;
  export let loading = false;

  const DOT_COUNT = 5;

  $: clampedScore = Math.min(1, Math.max(0, confidenceScore));
  $: fillPercent = Math.round(clampedScore * 100);
  $: filledDots = Math.round(clampedScore * DOT_COUNT);
  $: dotStates = Array.from({ length: DOT_COUNT }, (_, i) => i < filledDots);

  /**
   * Map a 0–1 confidence float to one of 5 semantic labels.
   * Boundaries: [0,0.2) early | [0.2,0.4) emerging | [0.4,0.6) moderate
   *             [0.6,0.8) strong | [0.8,1] very_strong
   */
  function confidenceLabel(score: number): string {
    if (score < 0.2) return 'early_signal';
    if (score < 0.4) return 'emerging_pattern';
    if (score < 0.6) return 'moderate_finding';
    if (score < 0.8) return 'strong_finding';
    return 'very_strong_finding';
  }

  $: confidenceLabelKey = confidenceLabel(clampedScore);

  $: showTier = Boolean(maturity && showMaturityBadge);
  $: tierPhase = maturity?.phase ?? null;
  $: tierLabel = tierPhase ? $_(`maturity.badge.${tierPhase}`, { values: { n: entryCount } }) : '';
  $: tierTooltip = tierPhase ? $_(`maturity.badge.${tierPhase}_tooltip`) : '';
  $: isTierUncertain = tierPhase === 'early_patterns' || tierPhase === 'provisional';
</script>

<span
  class="evidence"
  data-testid="insight-evidence"
  data-tier={currentTier}
  data-loading={loading ? 'true' : 'false'}
>
  {#if showTier}
    <span
      class="evidence__tier"
      class:evidence__tier--uncertain={isTierUncertain}
      data-testid="insight-maturity-badge"
      data-phase={tierPhase}
      title={tierTooltip}
      aria-label={tierTooltip}
    >
      {#if isTierUncertain}
        <span aria-hidden="true">!</span>
      {/if}
      <span>{tierLabel}</span>
    </span>
  {/if}

  {#if showConfidence}
    <span
      class="evidence__confidence"
      role="meter"
      aria-valuenow={clampedScore}
      aria-valuemin={0}
      aria-valuemax={1}
      aria-label={$_(`insights.confidence_label.${confidenceLabelKey}`)}
      data-testid="insight-confidence-meter"
    >
      <span class="evidence__dots" aria-hidden="true">
        {#each dotStates as filled, i (i)}
          <span class="evidence__dot" class:evidence__dot--filled={filled}></span>
        {/each}
      </span>
      <span class="evidence__label" data-testid="insight-confidence-label">
        {$_(`insights.confidence_label.${confidenceLabelKey}`)}
      </span>
      {#if detailed}
        <span class="evidence__percent" data-testid="insight-confidence-score-percent">
          {fillPercent}%
        </span>
      {/if}
    </span>
  {/if}

  {#if showSample}
    <span class="evidence__sample" data-testid="insight-evidence-sample">
      {$_('home.confidence_scale.entry_count', { values: { n: entryCount } })}
    </span>
  {/if}
</span>

<style>
  .evidence {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-2, 0.5rem);
  }

  .evidence[data-loading='true'] {
    opacity: 0.7;
  }

  .evidence__tier {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1, 0.25rem);
    flex-shrink: 0;
    width: fit-content;
    padding: 0.15rem 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-full);
    background: var(--color-surface-offset);
    color: var(--color-text);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 700;
    line-height: 1.3;
  }

  .evidence__tier[data-phase='early_patterns'] {
    border-color: color-mix(in srgb, var(--color-warning) 30%, var(--color-border));
    background: color-mix(in srgb, var(--color-warning) 12%, var(--color-surface));
    color: var(--color-warning);
  }

  .evidence__tier[data-phase='provisional'] {
    border-color: color-mix(in srgb, var(--color-warning) 42%, var(--color-border));
    background: color-mix(in srgb, var(--color-warning) 16%, var(--color-surface));
    color: var(--color-warning);
  }

  .evidence__tier[data-phase='robust'] {
    border-color: color-mix(in srgb, var(--color-success) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-success) 12%, var(--color-surface));
    color: var(--color-success);
  }

  .evidence__confidence {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1, 0.25rem);
    flex-shrink: 0;
  }

  .evidence__dots {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
  }

  .evidence__dot {
    width: 0.4rem;
    height: 0.4rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-border) 70%, transparent);
  }

  .evidence__dot--filled {
    background: var(--color-primary);
  }

  .evidence__label {
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    color: var(--color-text);
  }

  .evidence__percent {
    font-size: var(--text-xs, 0.75rem);
    font-weight: 700;
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }

  .evidence__sample {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
</style>
