<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse;

  const weekdays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

  function numericPayload(value: unknown): Record<string, number> {
    if (!value || typeof value !== 'object') return {};
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
        .map(([k, v]) => [k, v as number])
    );
  }

  $: averages = numericPayload(insight.payload.weekday_mood_avgs);
  $: values = weekdays.map((_, index) => averages[String(index)] ?? null);
  $: knownValues = values.filter((value): value is number => value !== null);
  $: maxValue = knownValues.length ? Math.max(...knownValues) : null;
  $: minValue = knownValues.length ? Math.min(...knownValues) : null;
  $: maxMood = Math.max(5, ...(knownValues.length ? knownValues : [5]));
</script>

<section
  class="weekday-pattern"
  id="weekday-pattern"
  data-testid="weekday-pattern-chart"
  aria-label={$_('home.weekday_pattern.heading')}
>
  <header class="weekday-pattern__header">
    <h2 class="weekday-pattern__heading">{$_('home.weekday_pattern.heading')}</h2>
    <span class="weekday-pattern__tier">{$_('home.weekday_pattern.early_signal')}</span>
  </header>

  <div class="weekday-pattern__chart" role="img" aria-label={$_('home.weekday_pattern.aria')}>
    {#each weekdays as weekday, index}
      {@const value = values[index]}
      <div
        class="weekday-pattern__bar-cell"
        data-highlight={value !== null && value === maxValue
          ? 'high'
          : value !== null && value === minValue
            ? 'low'
            : 'none'}
      >
        <span class="weekday-pattern__value">{value === null ? '-' : value.toFixed(1)}</span>
        <span
          class="weekday-pattern__bar"
          style={`height: ${value === null ? 4 : Math.max(8, (value / maxMood) * 72)}px`}
        ></span>
        <span class="weekday-pattern__label">{$_(`home.weekday.${weekday}`)}</span>
      </div>
    {/each}
  </div>

  <p class="weekday-pattern__statement">
    {insight.statement ?? $_('home.weekday_pattern.empty_statement')}
  </p>
  <p class="weekday-pattern__hint">{$_('home.weekday_pattern.hint')}</p>
</section>

<style>
  .weekday-pattern {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .weekday-pattern__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .weekday-pattern__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .weekday-pattern__tier {
    border-radius: 999px;
    padding: 0.18rem 0.55rem;
    font-size: 0.68rem;
    font-weight: 600;
    background: rgb(var(--color-primary-500, 59 130 246) / 0.1);
    color: rgb(var(--color-primary-700, 29 78 216));
  }

  .weekday-pattern__chart {
    min-height: 7rem;
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    align-items: end;
    gap: 0.35rem;
    padding: 0.75rem 0.5rem 0.55rem;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.45);
    background: rgb(var(--color-surface-100, 243 244 246) / 0.35);
    border-radius: 0.45rem;
  }

  .weekday-pattern__bar-cell {
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: end;
    gap: 0.25rem;
  }

  .weekday-pattern__value,
  .weekday-pattern__label,
  .weekday-pattern__hint {
    font-size: 0.72rem;
    color: var(--color-text-muted);
  }

  .weekday-pattern__bar {
    width: 100%;
    max-width: 1.4rem;
    min-height: 0.25rem;
    border-radius: 999px 999px 0.25rem 0.25rem;
    background: rgb(var(--color-primary-500, 59 130 246) / 0.45);
  }

  .weekday-pattern__bar-cell[data-highlight='high'] .weekday-pattern__bar {
    background: rgb(var(--color-success-500, 34 197 94));
  }

  .weekday-pattern__bar-cell[data-highlight='low'] .weekday-pattern__bar {
    background: rgb(var(--color-warning-500, 245 158 11));
  }

  .weekday-pattern__statement,
  .weekday-pattern__hint {
    margin: 0;
  }

  .weekday-pattern__statement {
    font-size: var(--text-sm, 0.88rem);
    line-height: 1.45;
  }
</style>
