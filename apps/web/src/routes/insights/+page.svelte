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
  import {
    listLatestInsights,
    type InsightMaturity,
    type InsightResponse,
  } from '$lib/api/insights';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { listDefaultTags, listVisibleTags } from '$lib/api/tags';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import InsightStageHeader from '$lib/components/insights/InsightStageHeader.svelte';
  import { mockEntries } from '$lib/dev/mockEntries';
  import { mockUserPreferences } from '$lib/dev/mockEntries';
  import { mockInsightMaturity, mockInsights } from '$lib/dev/mockInsights';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { shouldShowMaturityMilestone } from '$lib/utils/insightMaturityMilestones';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';

  let insights: InsightResponse[] = [];
  let loading = false;
  let error: string | null = null;
  let insightMaturity: InsightMaturity | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let entryCount = 0;
  let dayEntryDates: string[] = [];
  let inactiveTagIds: string[] = [];
  let detailView: 'findings' | 'matrix' = 'findings';

  async function loadInsights(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = null;
    try {
      if ($devForceVisualizations) {
        insights = mockInsights;
        insightMaturity = mockInsightMaturity;
        userPreferences = mockUserPreferences;
        dayEntryDates = dayEntryDatesFromIsoEntries(mockEntries);
        entryCount = dayEntryDates.length;
        inactiveTagIds = [];
        return;
      }

      const todayIso = localIsoDate(new Date());
      const startIso = shiftIsoDate(todayIso, -89);
      const [response, entryResponse, tagResponse, defaultTags, preferences] = await Promise.all([
        listLatestInsights({ limit: 50 }),
        listEntries({ start_date: startIso, end_date: todayIso }),
        listVisibleTags({ include_hidden: true }).catch(() => []),
        listDefaultTags().catch(() => []),
        fetchUserPreferences().catch(() => null),
      ]);
      insights = response.insights;
      insightMaturity = response.insight_maturity;
      userPreferences = preferences;
      dayEntryDates = dayEntryDatesFromIsoEntries(entryResponse);
      entryCount = dayEntryDates.length;
      const inactiveSlugs = new Set(
        tagResponse.filter((tag) => tag.is_hidden).map((tag) => tag.slug)
      );
      inactiveTagIds = [
        ...tagResponse.filter((tag) => tag.is_hidden).map((tag) => tag.id),
        ...defaultTags.filter((tag) => inactiveSlugs.has(tag.slug)).map((tag) => tag.id),
      ];
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      insights = [];
      insightMaturity = null;
      userPreferences = null;
      dayEntryDates = [];
      entryCount = 0;
      inactiveTagIds = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void loadInsights();
  });

  $: showMaturityMilestone = shouldShowMaturityMilestone(
    insightMaturity,
    userPreferences?.reached_milestone_keys
  );

  async function dismissMaturityMilestone(key: string): Promise<void> {
    const reached = new Set(userPreferences?.reached_milestone_keys ?? []);
    reached.add(key);
    const optimistic = {
      ...(userPreferences ?? {
        user_id: '',
        analytics_enabled: true,
        onboarding_retro_completed: false,
        onboarding_profile_completed: false,
        dismissed_insight_keys: [],
        last_seen_insight_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
      reached_milestone_keys: [...reached],
    };
    userPreferences = optimistic;
    try {
      userPreferences = await updateUserPreferences({
        reached_milestone_keys: optimistic.reached_milestone_keys,
      });
    } catch {
      // Optimistic dismissal for this session.
    }
  }
</script>

<svelte:head>
  <title>{$_('insights.page.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="insights-page">
  <ScreenHeader title={$_('insights.page.title')} subtitle={$_('insights.page.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('insights.page.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">
        {$_('auth.login.submit')}
      </Button>
    </Panel>
  {:else}
    {#if insightMaturity}
      <InsightStageHeader
        maturity={insightMaturity}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(e) => void dismissMaturityMilestone(e.detail.key)}
      />
    {/if}

    <div class="insights-page__view-toggle" aria-label={$_('insights.page.detail_views')}>
      <button
        type="button"
        class:insights-page__view-toggle--active={detailView === 'findings'}
        on:click={() => (detailView = 'findings')}
      >
        {$_('insights.page.findings_view')}
      </button>
      <button
        type="button"
        class:insights-page__view-toggle--active={detailView === 'matrix'}
        on:click={() => (detailView = 'matrix')}
      >
        {$_('insights.page.matrix_view')}
      </button>
    </div>

    {#if detailView === 'matrix'}
      <InsightMatrix {insights} />
    {:else}
      <InsightFeed
        {insights}
        maturity={insightMaturity}
        {loading}
        {error}
        {entryCount}
        {inactiveTagIds}
        on:retry={loadInsights}
      />
    {/if}
  {/if}
</main>

<style>
  .insights-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    padding: var(--space-4) 0 var(--space-8);
  }

  .insights-page__view-toggle {
    display: flex;
    gap: var(--space-2);
    padding: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    width: fit-content;
  }

  .insights-page__view-toggle button {
    min-height: 44px;
    padding: 0 var(--space-3);
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .insights-page__view-toggle--active {
    background: var(--color-primary-highlight);
    color: var(--color-primary) !important;
  }
</style>
