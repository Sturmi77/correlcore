<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightTier } from '$lib/api/insights';

  export let confidenceScore = 0.05;
  export let currentTier: InsightTier = 'none';
  export let entryCount = 0;
  export let loading = false;

  $: clampedScore = Math.min(1, Math.max(0, confidenceScore));
  $: fillPercent = Math.round(clampedScore * 100);
</script>

<section
  class="insight-confidence"
  data-testid="insight-confidence-scale"
  data-tier={currentTier}
  data-loading={loading ? 'true' : 'false'}
  aria-label={$_('home.confidence_scale.heading')}
>
  <header class="insight-confidence__header">
    <h2 class="insight-confidence__heading">{$_('home.confidence_scale.heading')}</h2>
    <span class="insight-confidence__score" data-testid="insight-confidence-score">
      {fillPercent}%
    </span>
  </header>

  <div class="insight-confidence__range" aria-hidden="true">
    <span>{$_('home.confidence_scale.low')}</span>
    <span>{$_('home.confidence_scale.high')}</span>
  </div>

  <div class="insight-confidence__track" role="presentation">
    <span
      class="insight-confidence__fill"
      data-testid="insight-confidence-fill"
      style={`width: ${fillPercent}%`}
    ></span>
  </div>

  <div class="insight-confidence__copy">
    <p class="insight-confidence__label">
      {$_(`home.confidence_scale.tier.${currentTier}`)}
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

  .insight-confidence__header,
  .insight-confidence__range,
  .insight-confidence__copy {
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

  .insight-confidence__score,
  .insight-confidence__label {
    font-size: 0.8rem;
    font-weight: 700;
  }

  .insight-confidence__range,
  .insight-confidence__meta {
    font-size: 0.72rem;
    color: var(--color-text-muted);
  }

  .insight-confidence__track {
    position: relative;
    width: 100%;
    height: 0.55rem;
    overflow: hidden;
    border-radius: 999px;
    background: rgb(var(--color-surface-300, 209 213 219) / 0.55);
  }

  .insight-confidence__fill {
    display: block;
    width: 0;
    height: 100%;
    border-radius: inherit;
    transition: width 220ms ease;
    background: rgb(var(--color-warning-500, 245 158 11));
  }

  .insight-confidence[data-tier='none'] .insight-confidence__fill,
  .insight-confidence[data-tier='early'] .insight-confidence__fill {
    background: rgb(var(--color-warning-500, 245 158 11));
  }

  .insight-confidence[data-tier='preliminary'] .insight-confidence__fill {
    background: rgb(var(--color-primary-500, 59 130 246));
  }

  .insight-confidence[data-tier='developing'] .insight-confidence__fill {
    background: rgb(var(--color-success-500, 34 197 94));
  }

  .insight-confidence[data-tier='robust'] .insight-confidence__fill {
    background: rgb(var(--color-success-600, 22 163 74));
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
