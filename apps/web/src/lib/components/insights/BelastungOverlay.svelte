<script lang="ts">
  /**
   * Phase 8 / #875 — opt-in Layer-1 Belastung & Erholung overlay (Mockup E5).
   * Not an insight_sections key; gated by belastung_overlay_enabled.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse;
  export let analyticsEnabled = true;

  $: payload = insight.payload ?? {};
  $: recentN = typeof payload.recent_n === 'number' ? payload.recent_n : insight.sample_n;
  $: priorN = typeof payload.prior_n === 'number' ? payload.prior_n : 0;
  $: fatigueRecent =
    typeof payload.fatigue_days_recent === 'number' ? payload.fatigue_days_recent : 0;
  $: fatiguePrior = typeof payload.fatigue_days_prior === 'number' ? payload.fatigue_days_prior : 0;
  $: recoveryRecent =
    typeof payload.recovery_days_recent === 'number' ? payload.recovery_days_recent : 0;
  $: recoveryPrior =
    typeof payload.recovery_days_prior === 'number' ? payload.recovery_days_prior : 0;
  $: signalHref = `/insights/signal/${insight.id}`;
</script>

<section
  class="belastung"
  data-testid="belastung-overlay"
  aria-label={$_('insights.belastung.aria')}
>
  <header class="belastung__header">
    <div>
      <h2 class="belastung__title">{$_('insights.belastung.title')}</h2>
      <p class="belastung__sub">{$_('insights.belastung.subtitle')}</p>
    </div>
    <span class="belastung__badge">{$_('insights.belastung.heuristic_badge')}</span>
  </header>

  <p class="belastung__statement" data-testid="belastung-statement">
    {insight.statement}
  </p>

  <p class="belastung__freq" data-testid="belastung-frequencies">
    {$_('insights.belastung.freq', {
      values: {
        fatigueRecent,
        recentN,
        fatiguePrior,
        priorN,
        recoveryRecent,
        recoveryPrior,
      },
    })}
  </p>

  <div class="belastung__actions">
    <a
      class="belastung__cta belastung__cta--primary"
      href={signalHref}
      data-testid="belastung-cta-intensity"
    >
      {$_('insights.belastung.cta_intensity')}
    </a>
    <a class="belastung__cta" href={signalHref} data-testid="belastung-cta-sleep">
      {$_('insights.belastung.cta_sleep')}
    </a>
  </div>

  <p class="belastung__disclaimer">
    {$_('insights.belastung.disclaimer')}
  </p>
  {#if !analyticsEnabled}
    <p class="belastung__note">{$_('insights.belastung.analytics_off')}</p>
  {/if}
</section>

<style>
  .belastung {
    display: flex;
    flex-direction: column;
    gap: var(--space-3, 0.75rem);
    padding: var(--space-4, 1rem);
    border: 1px solid oklch(from var(--color-text) l c h / 0.1);
    border-left: 3px solid var(--color-metric-stress, var(--color-primary));
    border-radius: var(--radius-lg, 0.75rem);
    background: var(--color-surface);
  }
  .belastung__header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: flex-start;
  }
  .belastung__title {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 650;
  }
  .belastung__sub {
    margin: 0.15rem 0 0;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
  .belastung__badge {
    flex-shrink: 0;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm, 0.35rem);
    border: 1px solid var(--color-border);
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    font-weight: 600;
  }
  .belastung__statement {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    line-height: 1.45;
  }
  .belastung__freq {
    margin: 0;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    line-height: 1.4;
  }
  .belastung__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .belastung__cta {
    display: inline-flex;
    padding: 0.35rem 0.7rem;
    border-radius: var(--radius-full, 999px);
    border: 1px solid var(--color-border);
    color: var(--color-text);
    font-size: var(--text-xs, 0.75rem);
    text-decoration: none;
    font-weight: 600;
  }
  .belastung__cta--primary {
    border-color: color-mix(in srgb, var(--color-primary) 40%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
    color: var(--color-primary);
  }
  .belastung__disclaimer,
  .belastung__note {
    margin: 0;
    font-size: var(--text-2xs);
    line-height: 1.5;
    color: var(--color-text-faint);
  }
</style>
