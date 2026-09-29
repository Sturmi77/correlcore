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
  $: maxAbs = bars
    ? Math.max(...bars.map((bar) => (bar.r === null ? 0 : Math.abs(bar.r))), 0.0001)
    : 1;
  $: peak = bars?.find((bar) => bar.active) ?? null;
  $: hasUnmeasured = bars?.some((bar) => bar.r === null) ?? false;
  // Stays empty when the comparator is unknown (pre-`good_direction` payload
  // with an unrecognised target): better to say nothing than to state the rule
  // backwards.
  $: goodRule =
    freq && freq.goodDirection
      ? $_(`insights.signal.lag_good_rule_${freq.goodDirection}`, {
          values: { target: freq.targetLabel ?? '', threshold: freq.goodThreshold },
        })
      : '';
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

  function directionLabel(r: number | null): string {
    if (r === null) return '';
    if (r > 0) return $_('insights.card.lag_profile_direction_positive');
    if (r < 0) return $_('insights.card.lag_profile_direction_negative');
    return '';
  }
</script>

{#if bars || freq}
  <section class="signal-lag" data-testid="signal-lag-evidence">
    <h2>{$_('insights.signal.lag_heading')}</h2>
    <p class="signal-lag__hint">{$_('insights.signal.lag_hint')}</p>
    {#if (freq?.lagDays ?? peak?.lag ?? 0) < 0}
      <p class="signal-lag__hint" data-testid="signal-lag-negative-note">
        {$_('insights.signal.lag_negative_note')}
      </p>
    {/if}

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
          {@const sign = bar.r === null ? 'none' : bar.r > 0 ? 'pos' : bar.r < 0 ? 'neg' : 'zero'}
          <div
            class="signal-lag__col"
            class:signal-lag__col--active={bar.active}
            class:signal-lag__col--unmeasured={bar.r === null}
          >
            <div class="signal-lag__track" data-sign={sign}>
              {#if bar.r === null}
                <!-- No paired observations at this lag. Deliberately not a zero
                     bar: "not measured" and "no association" are different claims. -->
                <div class="signal-lag__empty" data-testid="signal-lag-unmeasured"></div>
              {:else}
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
              {/if}
            </div>
            <span class="signal-lag__tick">{bar.lag}</span>
          </div>
        {/each}
      </div>
      {#if hasUnmeasured}
        <p class="signal-lag__unmeasured-note" data-testid="signal-lag-unmeasured-note">
          {$_('insights.signal.lag_unmeasured_note')}
        </p>
      {/if}
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
        {#if goodRule}
          <span class="signal-lag__good-rule" data-testid="signal-lag-good-rule">{goodRule}</span>
        {/if}
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

  /* Unmeasured lag: a hatched, empty slot. Reads as "nothing to show here",
     which a zero-height bar on the zero line would not. */
  .signal-lag__empty {
    width: 60%;
    max-width: 14px;
    height: 100%;
    margin: 0 auto;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-sm);
    background: transparent;
    opacity: 0.6;
  }

  .signal-lag__col--unmeasured .signal-lag__tick {
    color: var(--color-text-muted);
  }

  .signal-lag__unmeasured-note,
  .signal-lag__good-rule {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .signal-lag__unmeasured-note {
    margin: 0;
  }

  .signal-lag__good-rule {
    display: block;
  }

  .signal-lag__bar {
    width: 60%;
    max-width: 14px;
    /* token-exempt: 2px micro-bar cap; sm is the closest token */
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    background: var(--color-primary);
  }

  .signal-lag__half--neg .signal-lag__bar {
    /* token-exempt: 2px micro-bar cap; sm is the closest token */
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  }

  .signal-lag__tick {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
</style>
