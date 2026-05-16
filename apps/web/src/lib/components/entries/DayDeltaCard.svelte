<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { EntryDeltaResponse } from '$lib/api/entries';

  export let delta: EntryDeltaResponse | null = null;
  export let loading = false;

  const metrics = [
    { key: 'mood', labelKey: 'entry.delta.mood' },
    { key: 'energy', labelKey: 'entry.delta.energy' },
    { key: 'stress', labelKey: 'entry.delta.stress' },
  ] as const;

  $: hasComparison = Boolean(delta?.today && delta.previous);

  function deltaValue(metric: (typeof metrics)[number]['key']): number | null {
    return delta?.delta[metric] ?? null;
  }

  function formatDelta(value: number | null): string {
    if (value === null) return '—';
    if (value > 0) return `+${value}`;
    return String(value);
  }

  function direction(value: number | null): 'up' | 'down' | 'same' | 'unknown' {
    if (value === null) return 'unknown';
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'same';
  }
</script>

{#if hasComparison}
  <section class="day-delta" aria-label={$_('entry.delta.heading')} data-testid="day-delta-card">
    <header class="day-delta__header">
      <div>
        <h2>{$_('entry.delta.heading')}</h2>
        <p>{$_('entry.delta.subheading')}</p>
      </div>
      {#if loading}
        <span class="day-delta__loading">{$_('entry.delta.loading')}</span>
      {/if}
    </header>

    <dl class="day-delta__metrics">
      {#each metrics as metric}
        {@const value = deltaValue(metric.key)}
        <div class:day-delta__metric--unknown={value === null}>
          <dt>{$_(metric.labelKey)}</dt>
          <dd data-direction={direction(value)}>{formatDelta(value)}</dd>
        </div>
      {/each}
    </dl>

    {#if delta?.shared_tags.length}
      <div class="day-delta__tags" aria-label={$_('entry.delta.shared_tags')}>
        <span>{$_('entry.delta.shared_tags')}</span>
        <ul>
          {#each delta.shared_tags as tag}
            <li>{tag.name}</li>
          {/each}
        </ul>
      </div>
    {/if}
  </section>
{/if}

<style>
  .day-delta {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border-chart);
    border-radius: 8px;
    background: var(--color-surface-chart-bg);
  }

  .day-delta__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .day-delta__header h2,
  .day-delta__header p {
    margin: 0;
  }

  .day-delta__header h2 {
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .day-delta__header p,
  .day-delta__loading,
  .day-delta__tags span {
    font-size: var(--text-xs, 0.78rem);
    color: var(--color-text-muted);
  }

  .day-delta__metrics {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .day-delta__metrics div {
    min-width: 0;
    padding: var(--space-2);
    border-radius: 6px;
    background: var(--color-surface);
  }

  .day-delta__metrics dt {
    margin: 0;
    font-size: var(--text-xs, 0.78rem);
    color: var(--color-text-muted);
  }

  .day-delta__metrics dd {
    margin: 0.15rem 0 0;
    font-size: var(--text-base, 1rem);
    font-weight: 700;
  }

  .day-delta__metrics dd[data-direction='up'] {
    color: var(--color-primary);
  }

  .day-delta__metrics dd[data-direction='down'] {
    color: var(--color-warning);
  }

  .day-delta__metrics dd[data-direction='same'] {
    color: var(--color-text-muted);
  }

  .day-delta__tags {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .day-delta__tags ul {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .day-delta__tags li {
    border-radius: 999px;
    padding: 0.15rem 0.5rem;
    font-size: var(--text-xs, 0.78rem);
    background: color-mix(in srgb, var(--color-primary) 10%, transparent);
    color: var(--color-primary);
  }

  @media (max-width: 420px) {
    .day-delta__header {
      flex-direction: column;
    }

    .day-delta__metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
