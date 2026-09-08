<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { locale } from 'svelte-i18n';
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import type { InsightWorkerRunSummary } from '$lib/api/insights';
  import type { FaultyHomeContainer } from '$lib/utils/devHealth';
  import Button from '$lib/components/common/Button.svelte';
  import { formatHomeDate } from '$lib/utils/home';
  import { formatInsightWorkerRunBadge } from '$lib/utils/insightWorkerRunStatus';

  export let todayIso: string;
  export let todayEntry: EntryResponse | null = null;
  export let lastInsightRun: InsightWorkerRunSummary | null = null;
  export let faultyContainers: FaultyHomeContainer[] = [];
  export let loading = false;

  const dispatch = createEventDispatcher<{ logToday: void }>();

  $: dateLabel = formatHomeDate(todayIso, $locale ?? 'de');
  $: workContextKey = todayEntry
    ? (`entry.work_context.${todayEntry.work_context}` as const)
    : null;
  $: analysisBadge = formatInsightWorkerRunBadge(lastInsightRun, $_, {
    locale: $locale ?? 'en',
  });
</script>

<section class="home-today" data-testid="home-today-context" aria-live="polite">
  <div class="home-today__main">
    <p class="home-today__date">{dateLabel}</p>

    <div class="home-today__badges">
      {#if loading}
        <span class="home-today__badge home-today__badge--muted">{$_('home.loading_today')}</span>
      {:else}
        {#if todayEntry && workContextKey}
          <span
            class="home-today__badge home-today__badge--context"
            data-testid="home-work-context"
          >
            {$_(workContextKey)}
          </span>
          <span
            class="home-today__badge home-today__badge--success"
            data-testid="home-today-status"
          >
            {$_('home.entry_today_present')}
          </span>
        {:else}
          <span
            class="home-today__badge home-today__badge--warning"
            data-testid="home-today-status"
          >
            {$_('home.no_entry_today')}
          </span>
        {/if}
        {#if analysisBadge}
          <a
            href="/insights"
            class="home-today__badge home-today__badge--analysis home-today__badge--{analysisBadge.tone}"
            data-testid="home-analysis-status"
          >
            <span class="home-today__badge-label">{$_('home.worker_run.label')}</span>
            <span>{analysisBadge.text}</span>
          </a>
        {/if}
        {#each faultyContainers as container (container.name)}
          <a
            href="/dev"
            class="home-today__badge home-today__badge--warning"
            data-testid="home-container-status"
            data-container={container.name}
          >
            <span class="home-today__badge-label">{$_('home.container_health.label')}</span>
            <span>
              {$_(`home.container_health.${container.issue}`, {
                values: { name: container.name },
              })}
            </span>
          </a>
        {/each}
      {/if}
    </div>
  </div>

  {#if !loading}
    <!--
      #675: one button in a fixed position for both states; only the text and
      colour change (primary "log today" when no entry yet → secondary "edit"
      once recorded). The prior separate foot CTA was removed.
    -->
    <Button
      type="button"
      size="sm"
      variant={todayEntry ? 'secondary' : 'primary'}
      className="home-today__action"
      data-testid="home-today-action"
      on:click={() => dispatch('logToday')}
    >
      {todayEntry ? $_('home.cta_edit_entry') : $_('home.cta_log_today')}
    </Button>
  {/if}
</section>

<style>
  .home-today {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .home-today__main {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    min-width: 0;
  }

  .home-today__date {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-fg);
    text-wrap: balance;
  }

  .home-today__badges {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .home-today__badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: var(--text-xs);
    font-weight: 600;
    line-height: 1.3;
    text-decoration: none;
    color: inherit;
  }

  .home-today__badge-label {
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .home-today__badge--context {
    background: var(--color-primary-highlight);
    color: var(--color-primary);
    border: 1px solid color-mix(in oklch, var(--color-primary) 35%, transparent);
  }

  .home-today__badge--success {
    background: color-mix(in oklch, var(--color-success) 12%, transparent);
    color: var(--color-success);
  }

  .home-today__badge--warning {
    background: color-mix(in oklch, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }

  .home-today__badge--analysis.home-today__badge--success {
    background: color-mix(in oklch, var(--color-primary) 10%, transparent);
    color: var(--color-primary);
    border: 1px solid color-mix(in oklch, var(--color-primary) 28%, transparent);
  }

  .home-today__badge--analysis.home-today__badge--warning {
    background: color-mix(in oklch, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }

  .home-today__badge--muted {
    color: var(--color-text-muted);
  }

  :global(.home-today__action) {
    flex-shrink: 0;
    white-space: nowrap;
  }

  @media (max-width: 480px) {
    .home-today {
      flex-direction: column;
      align-items: stretch;
    }

    :global(.home-today__action) {
      width: 100%;
    }
  }
</style>
