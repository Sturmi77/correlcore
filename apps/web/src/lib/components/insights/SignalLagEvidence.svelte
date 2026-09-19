<script lang="ts">
  /**
   * Phase 14 / L8 — lag axis + two-denominator frequencies on signal detail.
   * Zeitversatz framing only (not same-day Spearman, not Compare Lag-1 Abfolge).
   */
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { lagProfileBars, parseLagFrequencyView } from '$lib/utils/lagInsight';

  export let insight: InsightResponse;

  $: bars = lagProfileBars(insight);
  $: freq = parseLagFrequencyView(insight);
  $: maxAbs = bars ? Math.max(...bars.map((bar) => Math.abs(bar.r)), 0.0001) : 1;
  $: peak = bars?.find((bar) => bar.active) ?? null;
  $: featureName =
    freq?.featureKey === 'sleep_minutes'
      ? $_('trends.metric.sleep_minutes')
      : freq?.featureKey === 'sleep_quality'
        ? $_('trends.metric.sleep_quality')
        : (freq?.featureLabel ?? $_('insights.signal.lag_feature_fallback'));

  function barHeight(r: number): number {
    const ratio = Math.abs(r) / maxAbs;
    return r === 0 ? 0 : Math.max(8, Math.round(ratio * 100));
  }

  function directionLabel(r: number): string {
    if (r > 0) return $_('insights.card.lag_profile_direction_positive');
    if (r < 0) return $_('insights.card.lag_profile_direction_negative');
    return '';
  }
</script>

{#if bars || freq}
  <section class="signal-lag" data-testid="signal-lag-evidence">
    <h2>{$_('insights.signal.lag_heading')}</h2>
    <p class="signal-lag__hint">{$_('insights.signal.lag_hint')}</p>

    {#if bars}
      <div
        class="signal-lag__bars"
        role="img"
        data-testid="signal-lag-bars"
        aria-label={$_('insights.card.lag_profile_aria', {
          values: {
            days: peak?.lag ?? 0,
            direction: directionLabel(peak?.r ?? 0),
          },
        })}
      >
        {#each bars as bar (bar.lag)}
          {@const sign = bar.r > 0 ? 'pos' : bar.r < 0 ? 'neg' : 'zero'}
          <div class="signal-lag__col" class:signal-lag__col--active={bar.active}>
            <div class="signal-lag__track" data-sign={sign}>
              <div class="signal-lag__half signal-lag__half--pos">
                {#if bar.r > 0}
                  <div class="signal-lag__bar" style={`height: ${barHeight(bar.r)}%`}></div>
                {/if}
              </div>
              <div class="signal-lag__zero" aria-hidden="true"></div>
              <div class="signal-lag__half signal-lag__half--neg">
                {#if bar.r < 0}
                  <div class="signal-lag__bar" style={`height: ${barHeight(bar.r)}%`}></div>
                {/if}
              </div>
            </div>
            <span class="signal-lag__tick">{bar.lag}</span>
          </div>
        {/each}
      </div>
    {/if}

    {#if freq}
      <p class="signal-lag__freq" data-testid="signal-lag-freq">
        {$_('insights.signal.lag_freq', {
          values: {
            feature: featureName,
            days: freq.lagDays,
            highGood: freq.highGood,
            highN: freq.highN,
            lowGood: freq.lowGood,
            lowN: freq.lowN,
          },
        })}
      </p>
    {/if}
  </section>
{/if}

<style>
  .signal-lag {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .signal-lag h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .signal-lag__hint,
  .signal-lag__freq {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .signal-lag__bars {
    display: flex;
    gap: var(--space-1);
    align-items: stretch;
    min-height: 96px;
  }

  .signal-lag__col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    opacity: 0.55;
  }

  .signal-lag__col--active {
    opacity: 1;
  }

  .signal-lag__track {
    flex: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    min-height: 72px;
  }

  .signal-lag__half {
    flex: 1;
    display: flex;
    justify-content: center;
  }

  .signal-lag__half--pos {
    align-items: flex-end;
  }

  .signal-lag__half--neg {
    align-items: flex-start;
  }

  .signal-lag__zero {
    height: 1px;
    width: 100%;
    background: var(--color-border);
  }

  .signal-lag__bar {
    width: 60%;
    max-width: 14px;
    border-radius: 2px 2px 0 0;
    background: var(--color-primary);
  }

  .signal-lag__half--neg .signal-lag__bar {
    border-radius: 0 0 2px 2px;
  }

  .signal-lag__tick {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
</style>
