<script lang="ts">
  /**
   * /insights/history — Insight timeline / archive (#601 Phase 2)
   */
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import {
    listInsightHistory,
    type InsightHistoryItem,
    type InsightHistoryVisibility,
  } from '$lib/api/insights';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightHistoryTimeline from '$lib/components/insights/InsightHistoryTimeline.svelte';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  const PAGE_SIZE = 40;

  let items: InsightHistoryItem[] = [];
  let status: InsightHistoryVisibility = 'all';
  let total = 0;
  let loading = true;
  let error: string | null = null;
  let loadSeq = 0;

  async function loadHistory(append = false): Promise<void> {
    const seq = ++loadSeq;
    const requestedStatus = status;
    loading = true;
    error = null;
    try {
      const response = await listInsightHistory({
        status: requestedStatus,
        limit: PAGE_SIZE,
        offset: append ? items.length : 0,
      });
      if (seq !== loadSeq || requestedStatus !== status) return;
      items = append ? [...items, ...response.insights] : response.insights;
      total = response.total;
    } catch (err) {
      if (seq !== loadSeq || requestedStatus !== status) return;
      error = err instanceof Error ? err.message : $_('insights.history.error');
      if (!append) {
        items = [];
        total = 0;
      }
    } finally {
      if (seq === loadSeq) {
        loading = false;
      }
    }
  }

  function setStatus(next: InsightHistoryVisibility): void {
    if (next === status) return;
    status = next;
    void loadHistory();
  }

  onMount(() => {
    if ($auth.status !== 'authenticated') {
      void goto('/auth/login?next=/insights/history');
      return;
    }
    void loadHistory();
    return registerPageRefresh(() => loadHistory());
  });
</script>

<svelte:head>
  <title>{$_('insights.history.title')} - {$_('app.name')}</title>
</svelte:head>

<div class="history-page">
  <ScreenHeader
    title={$_('insights.history.title')}
    subtitle={$_('insights.history.subtitle')}
    back={{ href: '/insights', label: $_('nav.insights') }}
  />

  <InsightHistoryTimeline
    {items}
    {status}
    {loading}
    {error}
    {total}
    on:statusChange={(event) => setStatus(event.detail.status)}
    on:loadMore={() => void loadHistory(true)}
  />
</div>

<style>
  .history-page {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-4);
  }
</style>
