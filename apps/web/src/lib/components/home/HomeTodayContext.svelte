<script lang="ts">
  import { locale } from 'svelte-i18n';
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import { formatHomeDate } from '$lib/utils/home';

  export let todayIso: string;
  export let todayEntry: EntryResponse | null = null;
  export let loading = false;

  $: dateLabel = formatHomeDate(todayIso, $locale ?? 'de');
  $: workContextKey = todayEntry
    ? (`entry.work_context.${todayEntry.work_context}` as const)
    : null;
</script>

<section class="home-today" data-testid="home-today-context" aria-live="polite">
  <p class="home-today__date">{dateLabel}</p>

  {#if loading}
    <span class="home-today__badge home-today__badge--muted">{$_('home.loading_today')}</span>
  {:else if todayEntry && workContextKey}
    <span class="home-today__badge home-today__badge--context" data-testid="home-work-context">
      {$_(workContextKey)}
    </span>
    <span class="home-today__badge home-today__badge--success" data-testid="home-today-status">
      {$_('home.entry_today_present')}
    </span>
  {:else}
    <span class="home-today__badge home-today__badge--warning" data-testid="home-today-status">
      {$_('home.no_entry_today')}
    </span>
  {/if}
</section>

<style>
  .home-today {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    text-align: center;
  }

  .home-today__date {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--color-fg);
    text-wrap: balance;
  }

  .home-today__badge {
    display: inline-flex;
    align-items: center;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: var(--text-xs);
    font-weight: 600;
    line-height: 1.3;
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

  .home-today__badge--muted {
    color: var(--color-text-muted);
  }
</style>
