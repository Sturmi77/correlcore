<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import type { EntryStreakResponse } from '$lib/api/stats';

  export let streak: EntryStreakResponse | null = null;
  export let cycleEntries: EntryResponse[] = [];
</script>

<section
  class="trends-health"
  data-testid="trends-health-context"
  aria-label={$_('trends.health.heading')}
>
  <div class="trends-health__intro">
    <h2>{$_('trends.health.heading')}</h2>
    <p>{$_('trends.health.body')}</p>
  </div>
  <section class="trends-health__consistency" aria-label={$_('trends.consistency.heading')}>
    <div>
      <span>{$_('trends.consistency.current')}</span>
      <strong>{streak?.current_streak ?? '-'}</strong>
    </div>
    <div>
      <span>{$_('trends.consistency.longest')}</span>
      <strong>{streak?.longest_streak ?? '-'}</strong>
    </div>
    <div>
      <span>{$_('trends.consistency.total')}</span>
      <strong>{streak?.total_entry_days ?? '-'}</strong>
    </div>
  </section>
  {#if cycleEntries.length > 0}
    <section class="trends-health__cycle" aria-label={$_('trends.cycle.heading')}>
      <div>
        <h3>{$_('trends.cycle.heading')}</h3>
        <p>{$_('trends.cycle.body')}</p>
      </div>
      <div class="trends-health__cycle-strip">
        {#each cycleEntries.slice(0, 14) as entry}
          <span title={`${entry.entry_date}: ${entry.cycle_day}`}>
            <small>{entry.entry_date.slice(5)}</small>
            <strong>{entry.cycle_day}</strong>
          </span>
        {/each}
      </div>
    </section>
  {/if}
</section>

<style>
  .trends-health {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .trends-health__intro h2,
  .trends-health__intro p,
  .trends-health__cycle h3,
  .trends-health__cycle p {
    margin: 0;
  }

  .trends-health__intro h2 {
    font-size: var(--text-lg);
  }

  .trends-health__intro p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
  }

  .trends-health__consistency {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--screen-gap);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface-2) 72%, transparent);
  }

  .trends-health__consistency div {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .trends-health__consistency span {
    font-size: var(--text-xs);
    opacity: 0.7;
  }

  .trends-health__consistency strong {
    font-size: var(--text-2xl);
  }

  .trends-health__cycle {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface-2) 72%, transparent);
  }

  .trends-health__cycle h3 {
    font-size: var(--text-base);
  }

  .trends-health__cycle-strip {
    display: flex;
    gap: var(--space-2);
    overflow-x: auto;
    padding-bottom: var(--space-1);
  }

  .trends-health__cycle-strip span {
    min-width: 3.75rem;
    min-height: 3.75rem;
    display: grid;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--color-primary) 22%, var(--color-border));
    border-radius: var(--radius-sm);
    background: var(--color-surface);
  }

  .trends-health__cycle-strip small {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .trends-health__cycle-strip strong {
    font-size: var(--text-lg);
  }

  @media (max-width: 480px) {
    .trends-health__consistency {
      grid-template-columns: 1fr;
    }
  }
</style>
