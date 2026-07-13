<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { fetchHealthSummary, type HealthSummary } from '$lib/api/health';

  let summary: HealthSummary | null = null;
  let error: string | null = null;
  let loading = true;
  let controller: AbortController;

  async function load() {
    loading = true;
    error = null;
    controller = new AbortController();
    try {
      summary = await fetchHealthSummary(controller.signal);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        error = (e as Error).message ?? $_('status.unknown_error');
      }
    } finally {
      loading = false;
    }
  }

  // Poll every 30 s
  let interval: ReturnType<typeof setInterval>;
  onMount(() => {
    load();
    interval = setInterval(load, 30_000);
  });
  onDestroy(() => {
    clearInterval(interval);
    controller?.abort();
  });

  function statusTone(status: string): 'ok' | 'warning' | 'error' {
    if (status === 'ok' || status === 'ready') return 'ok';
    if (status === 'degraded') return 'warning';
    return 'error';
  }
</script>

<svelte:head>
  <title>{$_('status.title')} — CorrelCore</title>
</svelte:head>

<main class="flex-1 flex flex-col items-center p-6 gap-6 max-w-lg mx-auto w-full">
  <h1 class="h2 self-start">{$_('status.title')}</h1>

  {#if loading && !summary}
    <p class="opacity-60 text-sm">{$_('status.checking')}</p>
  {:else if error}
    <div class="card p-4 variant-ghost-error w-full">
      <p class="text-sm">{$_('status.api_error')} <code>{error}</code></p>
      <button class="btn btn-sm variant-ghost-surface mt-2" on:click={load}>
        {$_('status.retry')}
      </button>
    </div>
  {:else if summary}
    <!-- Overall status -->
    <div class="card p-5 variant-ghost-surface w-full flex items-center gap-4">
      <span class="status-dot status-dot--{statusTone(summary.status)}" aria-hidden="true"></span>
      <div>
        <p class="status-text status-text--{statusTone(summary.status)} capitalize">{summary.status}</p>
        <p class="text-xs opacity-60">API v{summary.version}</p>
      </div>
    </div>

    <!-- Components -->
    <div class="card p-5 variant-ghost-surface w-full flex flex-col gap-3">
      <h2 class="text-sm font-semibold opacity-70 uppercase tracking-wider">
        {$_('status.components')}
      </h2>
      {#each summary.readiness.components as component}
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="status-dot status-dot--{statusTone(component.status)} status-dot--sm" aria-hidden="true"></span>
            <span class="text-sm capitalize">{component.name}</span>
          </div>
          <span class="text-xs status-text status-text--{statusTone(component.status)} capitalize font-medium">
            {component.status}
            {#if component.detail}
              <span class="opacity-60">({component.detail})</span>
            {/if}
          </span>
        </div>
      {/each}
    </div>

    <p class="text-xs opacity-40 self-end">{$_('status.auto_refresh')}</p>
  {/if}
</main>

<style>
  .status-dot {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: var(--radius-full);
    flex-shrink: 0;
  }

  .status-dot--sm {
    width: 0.5rem;
    height: 0.5rem;
  }

  .status-dot--ok {
    background: var(--color-success);
  }

  .status-dot--warning {
    background: var(--color-warning);
  }

  .status-dot--error {
    background: var(--color-error);
  }

  .status-text {
    font-weight: 600;
  }

  .status-text--ok {
    color: var(--color-success);
  }

  .status-text--warning {
    color: var(--color-warning);
  }

  .status-text--error {
    color: var(--color-error);
  }
</style>
