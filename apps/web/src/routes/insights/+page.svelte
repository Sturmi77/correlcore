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
  import { fetchSymptomHeatmap, type SymptomHeatmapResponse } from '$lib/api/stats';
  import {
    fetchSymptomTagCooccurrence,
    fetchTagCooccurrence,
    listLatestInsights,
    type InsightMaturity,
    type InsightResponse,
    type TagCooccurrenceRange,
    type SymptomTagCooccurrenceResponse,
    type TagCooccurrenceResponse,
  } from '$lib/api/insights';
  import { listDefaultTags, listTagsForEntry, listVisibleTags } from '$lib/api/tags';
  import { listVisibleSymptoms, listSymptomsForEntry } from '$lib/api/symptoms';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import InsightStageHeader from '$lib/components/insights/InsightStageHeader.svelte';
  import CooccurrenceEntrySheet from '$lib/components/insights/CooccurrenceEntrySheet.svelte';
  import TagCooccurrenceHeatmap from '$lib/components/insights/TagCooccurrenceHeatmap.svelte';
  import SymptomAnalyticsSection from '$lib/components/insights/symptoms/SymptomAnalyticsSection.svelte';
  import type { EntryHistoryDetail } from '$lib/components/trends/EntryHistorySheet.svelte';
  import { mockEntries } from '$lib/dev/mockEntries';
  import { mockUserPreferences } from '$lib/dev/mockEntries';
  import {
    mockSymptomHeatmap,
    mockSymptomTagCooccurrence,
    mockTagCooccurrence,
  } from '$lib/dev/mockTrends';
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
  let cooccurrenceRange: TagCooccurrenceRange = '90d';
  let cooccurrence: TagCooccurrenceResponse | null = null;
  let cooccurrenceLoading = false;
  let cooccurrenceHistoryOpen = false;
  let cooccurrenceHistoryTitle = '';
  let cooccurrenceHistoryLoading = false;
  let cooccurrenceHistoryError = '';
  let cooccurrenceHistoryDetails: EntryHistoryDetail[] = [];
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let symptomCooccurrence: SymptomTagCooccurrenceResponse | null = null;
  let symptomCooccurrenceLoading = false;
  let showInsightSymptoms = true;

  const INSIGHT_SYMPTOMS_STORAGE_KEY = 'cc_insights_symptoms';

  function setShowInsightSymptoms(value: boolean): void {
    showInsightSymptoms = value;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(INSIGHT_SYMPTOMS_STORAGE_KEY, value ? 'true' : 'false');
    }
  }

  async function loadCooccurrence(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    cooccurrenceLoading = true;
    try {
      if ($devForceVisualizations) {
        cooccurrence = mockTagCooccurrence;
        return;
      }
      cooccurrence = await fetchTagCooccurrence({ range: cooccurrenceRange, min_count: 2 });
    } catch {
      cooccurrence = null;
    } finally {
      cooccurrenceLoading = false;
    }
  }

  async function loadSymptomCooccurrence(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    symptomCooccurrenceLoading = true;
    try {
      if ($devForceVisualizations) {
        symptomCooccurrence = mockSymptomTagCooccurrence;
        return;
      }
      symptomCooccurrence = await fetchSymptomTagCooccurrence({
        range: cooccurrenceRange,
        min_count: 3,
      });
    } catch {
      symptomCooccurrence = null;
    } finally {
      symptomCooccurrenceLoading = false;
    }
  }

  async function openCooccurrenceHistory(
    event: CustomEvent<{
      tagAId: string;
      tagBId: string;
      tagAName: string;
      tagBName: string;
      startDate: string;
      endDate: string;
    }>
  ): Promise<void> {
    const { tagAId, tagBId, tagAName, tagBName, startDate, endDate } = event.detail;
    cooccurrenceHistoryOpen = true;
    cooccurrenceHistoryTitle = `${tagAName} + ${tagBName}`;
    cooccurrenceHistoryLoading = true;
    cooccurrenceHistoryError = '';
    cooccurrenceHistoryDetails = [];
    try {
      if ($devForceVisualizations) {
        cooccurrenceHistoryDetails = mockEntries
          .filter((entry) => entry.entry_date >= startDate && entry.entry_date <= endDate)
          .slice(0, 3)
          .map((entry) => ({
            entry,
            tags: [tagAName, tagBName],
            symptoms: [],
          }));
        return;
      }

      const [entries, visibleSymptoms] = await Promise.all([
        listEntries({ start_date: startDate, end_date: endDate, limit: 365 }),
        listVisibleSymptoms(),
      ]);
      const symptomNames = new Map(visibleSymptoms.map((symptom) => [symptom.id, symptom.name]));
      const details = await Promise.all(
        entries.map(async (entry) => {
          const [tags, symptoms] = await Promise.all([
            listTagsForEntry(entry.id),
            listSymptomsForEntry(entry.id),
          ]);
          const tagIds = new Set(tags.map((tag) => tag.id));
          if (!tagIds.has(tagAId) || !tagIds.has(tagBId)) return null;
          return {
            entry,
            tags: tags.map((tag) => tag.name),
            symptoms: symptoms.map((symptom) => ({
              name: symptomNames.get(symptom.symptom_id) ?? $_('symptom.picker_label'),
              intensity: symptom.intensity,
            })),
          } satisfies EntryHistoryDetail;
        })
      );
      cooccurrenceHistoryDetails = details.filter(
        (detail): detail is EntryHistoryDetail => detail !== null
      );
    } catch (err) {
      cooccurrenceHistoryError = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      cooccurrenceHistoryLoading = false;
    }
  }

  async function loadInsights(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = null;
    try {
      if ($devForceVisualizations) {
        insights = mockInsights;
        insightMaturity = mockInsightMaturity;
        userPreferences = mockUserPreferences;
        symptomHeatmap = mockSymptomHeatmap;
        symptomCooccurrence = mockSymptomTagCooccurrence;
        dayEntryDates = dayEntryDatesFromIsoEntries(mockEntries);
        entryCount = dayEntryDates.length;
        inactiveTagIds = [];
        return;
      }

      const todayIso = localIsoDate(new Date());
      const startIso = shiftIsoDate(todayIso, -89);
      const [response, entryResponse, tagResponse, defaultTags, preferences, nextSymptomHeatmap] =
        await Promise.all([
          listLatestInsights({ limit: 50 }),
          listEntries({ start_date: startIso, end_date: todayIso }),
          listVisibleTags({ include_hidden: true }).catch(() => []),
          listDefaultTags().catch(() => []),
          fetchUserPreferences().catch(() => null),
          fetchSymptomHeatmap({ start_date: startIso, end_date: todayIso }).catch(() => null),
        ]);
      insights = response.insights;
      insightMaturity = response.insight_maturity;
      userPreferences = preferences;
      symptomHeatmap = nextSymptomHeatmap;
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
      symptomHeatmap = null;
      symptomCooccurrence = null;
      dayEntryDates = [];
      entryCount = 0;
      inactiveTagIds = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    showInsightSymptoms = localStorage.getItem(INSIGHT_SYMPTOMS_STORAGE_KEY) !== 'false';
    void loadInsights();
    void loadCooccurrence();
    void loadSymptomCooccurrence();
  });

  $: showMaturityMilestone = shouldShowMaturityMilestone(
    insightMaturity,
    userPreferences?.reached_milestone_keys
  );
  $: showSymptomAnalytics =
    showInsightSymptoms && (!insightMaturity || insightMaturity.phase !== 'collecting');

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
      <label class="insights-page__symptom-toggle">
        <input
          type="checkbox"
          checked={showInsightSymptoms}
          on:change={(event) => setShowInsightSymptoms(event.currentTarget.checked)}
        />
        {$_('insights.page.symptoms_toggle')}
      </label>
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
      {#if showSymptomAnalytics}
        <SymptomAnalyticsSection
          heatmap={symptomHeatmap}
          cooccurrence={symptomCooccurrence}
          cooccurrenceLoading={symptomCooccurrenceLoading}
          phase={insightMaturity?.phase ?? null}
          {loading}
        />
      {/if}
    {/if}

    <TagCooccurrenceHeatmap
      data={cooccurrence}
      loading={cooccurrenceLoading}
      range={cooccurrenceRange}
      on:rangeChange={(event) => {
        cooccurrenceRange = event.detail.range;
        void loadCooccurrence();
        void loadSymptomCooccurrence();
      }}
      on:selectPair={(event) => void openCooccurrenceHistory(event)}
    />

    <CooccurrenceEntrySheet
      open={cooccurrenceHistoryOpen}
      title={cooccurrenceHistoryTitle}
      loading={cooccurrenceHistoryLoading}
      error={cooccurrenceHistoryError}
      details={cooccurrenceHistoryDetails}
      on:close={() => (cooccurrenceHistoryOpen = false)}
    />
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

  .insights-page__symptom-toggle {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: 0 var(--space-3);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .insights-page__view-toggle--active {
    background: var(--color-primary-highlight);
    color: var(--color-primary) !important;
  }
</style>
