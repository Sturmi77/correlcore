<script lang="ts">
  /**
   * InsightConfidenceScale — ADR-0018.
   *
   * Renders a labelled progress bar that communicates insight confidence
   * without exposing a raw percentage on collapsed cards.
   *
   * Props
   * -----
   * confidenceScore  Float 0–1. Clamped internally.
   * currentTier      InsightTier from the API (used for i18n tier copy).
   * entryCount       Raw sample size shown as metadata.
   * loading          Dims component while parent data is loading.
   * showRawPercent   Pass true only from expanded InsightCard Level 2.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightTier } from '$lib/api/insights';

  export let confidenceScore = 0.05;
  export let currentTier: InsightTier = 'none';
  export let entryCount = 0;
  export let loading = false;
  /** Set true only in the expanded (Level 2) InsightCard view. */
  export let showRawPercent = false;

  $: clampedScore = Math.min(1, Math.max(0, confidenceScore));
  $: fillPercent = Math.round(clampedScore * 100);

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

  $: labelKey = confidenceLabel(clampedScore);
</script>

<section
  class="insight-confidence"
  data-testid="insight-confidence-scale"
  data-tier={currentTier}
  data-loading={loading ? 'true' : 'false'}
>
  <header class="insight-confidence__header">
    <h2 class="insight-confidence__heading">
      {$_('home.confidence_scale.heading')}
    </h2>
    {#if showRawPercent}
      <span
        class="insight-confidence__score"
        data-testid="insight-confidence-score-percent"
        aria-hidden="true"
      >
        {fillPercent}%
      </span>
    {/if}
  </header>

  <!--
    role="meter" communicates the scalar value to assistive technology.
    aria-label duplicates the section heading for AT that reads the meter
    without surrounding context.
  -->
  <div
    class="insight-confidence__track"
    role="meter"
    aria-valuenow={clampedScore}
    aria-valuemin={0}
    aria-valuemax={1}
    aria-label={$_('home.confidence_scale.heading')}
    data-testid="insight-confidence-meter"
  >
    <span
      class="insight-confidence__fill"
      data-testid="insight-confidence-fill"
      style={`width: ${fillPercent}%`}
    ></span>
  </div>

  <div class="insight-confidence__copy">
    <p
      class="insight-confidence__label"
      data-testid="insight-confidence-label"
    >
      {$_(`insights.confidence_label.${labelKey}`)}
    </p>
    <p class="insight-confidence__meta">
      {$_('home.confidence_scale.entry_count', { values: { n: entryCount } })}
    </p>
  </div>
</section>

<style>
  .insight-confidence {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .insight-confidence__header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .insight-confidence__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .insight-confidence__score {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--color-text-muted);
  }

  .insight-confidence__track {
    position: relative;
    width: 100%;
    height: 0.55rem;
    overflow: hidden;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-border) 55%, transparent);
  }

  .insight-confidence__fill {
    display: block;
    width: 0;
    height: 100%;
    border-radius: inherit;
    transition: width 220ms ease;
    background: var(--color-primary);
  }

  .insight-confidence__copy {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .insight-confidence__label {
    font-size: 0.8rem;
    font-weight: 700;
    margin: 0;
  }

  .insight-confidence__meta {
    font-size: 0.72rem;
    color: var(--color-text-muted);
    margin: 0;
  }

  .insight-confidence[data-loading='true'] {
    opacity: 0.7;
  }

  @media (prefers-reduced-motion: reduce) {
    .insight-confidence__fill {
      transition: none;
    }
  }

  @media (max-width: 420px) {
    .insight-confidence__copy {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.15rem;
    }
  }
</style>
