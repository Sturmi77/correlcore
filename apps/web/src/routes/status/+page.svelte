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
        error = (e as Error).message ?? 'Unknown error';
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

  function statusColor(status: string): string {
    if (status === 'ok' || status === 'ready') return 'text-success-500';
    if (status === 'degraded') return 'text-warning-500';
    return 'text-error-500';
  }

  function statusDot(status: string): string {
    if (status === 'ok' || status === 'ready') return 'bg-success-500';
    if (status === 'degraded') return 'bg-warning-500';
    return 'bg-error-500';
  }
</script>

<svelte:head>
  <title>System Status — MoodSync</title>
</svelte:head>

<main class="flex-1 flex flex-col items-center p-6 gap-6 max-w-lg mx-auto w-full">
  <h1 class="h2 self-start">System Status</h1>

  {#if loading && !summary}
    <p class="opacity-60 text-sm">Checking…</p>

  {:else if error}
    <div class="card p-4 variant-ghost-error w-full">
      <p class="text-sm">Could not reach the API: <code>{error}</code></p>
      <button class="btn btn-sm variant-ghost-surface mt-2" on:click={load}>Retry</button>
    </div>

  {:else if summary}
    <!-- Overall status -->
    <div class="card p-5 variant-ghost-surface w-full flex items-center gap-4">
      <span class="w-3 h-3 rounded-full {statusDot(summary.status)} flex-shrink-0"></span>
      <div>
        <p class="font-semibold {statusColor(summary.status)} capitalize">{summary.status}</p>
        <p class="text-xs opacity-60">API v{summary.version}</p>
      </div>
    </div>

    <!-- Components -->
    <div class="card p-5 variant-ghost-surface w-full flex flex-col gap-3">
      <h2 class="text-sm font-semibold opacity-70 uppercase tracking-wider">Components</h2>
      {#each summary.readiness.components as component}
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full {statusDot(component.status)} flex-shrink-0"></span>
            <span class="text-sm capitalize">{component.name}</span>
          </div>
          <span class="text-xs {statusColor(component.status)} capitalize font-medium">
            {component.status}
            {#if component.detail}
              <span class="opacity-60">({component.detail})</span>
            {/if}
          </span>
        </div>
      {/each}
    </div>

    <p class="text-xs opacity-40 self-end">Auto-refreshes every 30 s</p>
  {/if}
</main>
