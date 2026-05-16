<script lang="ts">
  /**
   * /insights — InsightFeed page (M3.1, Issue #164)
   *
   * Replaces the old raw-list rendering with the InsightFeed component.
   * - Sort: confidence × |effect_size| descending (done inside InsightFeed)
   * - Filter tabs: All | Mood | Symptoms | Sleep
   * - Inline error banner — no full-page crash on API failure
   * - Empty state / skeleton delegated to InsightFeed
   *
   * InsightMatrix (M3.1 Step 4 / TODO-5) is rendered above the feed
   * to show the correlation matrix for pointbiserial insights.
   */
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listEntries } from '$lib/api/entries';
  import { listLatestInsights, type InsightResponse } from '$lib/api/insights';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import { mockEntries } from '$lib/dev/mockEntries';
  import { mockInsights } from '$lib/dev/mockInsights';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';

  let insights: InsightResponse[] = [];
  let loading = false;
  let error: string | null = null;
  let entryCount = 0;
  let dayEntryDates: string[] = [];

  async function loadInsights(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = null;
    try {
      if ($devForceVisualizations) {
        insights = mockInsights;
        dayEntryDates = dayEntryDatesFromIsoEntries(mockEntries);
        entryCount = dayEntryDates.length;
        return;
      }

      const todayIso = localIsoDate(new Date());
      const startIso = shiftIsoDate(todayIso, -89);
      const [response, entryResponse] = await Promise.all([
        listLatestInsights({ limit: 50 }),
        listEntries({ start_date: startIso, end_date: todayIso }),
      ]);
      insights = response.insights;
      dayEntryDates = dayEntryDatesFromIsoEntries(entryResponse);
      entryCount = dayEntryDates.length;
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      insights = [];
      dayEntryDates = [];
      entryCount = 0;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void loadInsights();
  });
</script>

<svelte:head>
  <title>{$_('insights.page.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="insights-page">
  <header class="insights-page__top">
    <a class="btn btn-sm variant-ghost-surface" href="/">{$_('nav.home')}</a>
    <ThemeToggle testId="insights-theme-toggle" />
  </header>

  {#if $auth.status !== 'authenticated'}
    <section class="insights-page__panel">
      <p>{$_('insights.page.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">
        {$_('auth.login.submit')}
      </a>
    </section>
  {:else}
    {#if !loading && insights.length > 0}
      <InsightMatrix {insights} />
    {/if}

    <InsightFeed {insights} {loading} {error} {entryCount} {dayEntryDates} on:retry={loadInsights} />
  {/if}
</main>

<style>
  .insights-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    padding: var(--space-4) 0 var(--space-8);
  }

  .insights-page__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .insights-page__panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid oklch(from var(--color-text) l c h / 0.1);
    border-radius: var(--radius-lg);
  }
</style>
