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
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { insightStore } from '$lib/stores/insights';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchSymptomHeatmap, type SymptomHeatmapResponse } from '$lib/api/stats';
  import {
    fetchSymptomTagCooccurrence,
    fetchTagClusters,
    fetchTagCooccurrence,
    listLatestInsights,
    type InsightMaturity,
    type InsightResponse,
    type SymptomTagCooccurrenceCell,
    type TagCooccurrenceRange,
    type SymptomTagCooccurrenceResponse,
    type TagClustersResponse,
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
  import TabBar from '$lib/components/common/TabBar.svelte';
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import InsightStageHeader from '$lib/components/insights/InsightStageHeader.svelte';
  import MobileInsightLead from '$lib/components/insights/MobileInsightLead.svelte';
  import CooccurrenceEntrySheet from '$lib/components/insights/CooccurrenceEntrySheet.svelte';
  import CorrelationDisclaimer from '$lib/components/insights/CorrelationDisclaimer.svelte';
  import TagCooccurrenceHeatmap from '$lib/components/insights/TagCooccurrenceHeatmap.svelte';
  import TagGroupsSection from '$lib/components/insights/TagGroupsSection.svelte';
  import SymptomAnalyticsSection from '$lib/components/insights/symptoms/SymptomAnalyticsSection.svelte';
  import SymptomCooccurrenceDetailSheet from '$lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte';
  import EntryHistorySheet, {
    type EntryHistoryDetail,
  } from '$lib/components/trends/EntryHistorySheet.svelte';
  import type { CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';
  import { mockEntries } from '$lib/dev/mockEntries';
  import { mockUserPreferences } from '$lib/dev/mockEntries';
  import {
    mockSymptomHeatmap,
    mockSymptomTagCooccurrenceByRange,
    mockTagClusters,
    mockTagCooccurrenceByRange,
  } from '$lib/dev/mockTrends';
  import { mockInsightMaturity, mockInsights } from '$lib/dev/mockInsights';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { analysisRange, setAnalysisRange } from '$lib/stores/analysisRange';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { shouldShowMaturityMilestone } from '$lib/utils/insightMaturityMilestones';
  import {
    getInsightFeedFilterTabs,
    rankedInsightsForTab,
    type InsightFeedFilterTab,
  } from '$lib/utils/insightFeedFilter';
  import { countMatrixInsights, MATRIX_TAB_MIN_INSIGHTS } from '$lib/utils/insightMatrixGate';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import { timeseriesRangeToCooccurrence } from '$lib/utils/analysisRange';
  import type { TimeseriesRange } from '$lib/api/stats';

  type DetailView = 'findings' | 'matrix';

  let insights: InsightResponse[] = [];
  let loading = false;
  let insightsLoaded = false;
  let error: string | null = null;
  let insightMaturity: InsightMaturity | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let entryCount = 0;
  let dayEntryDates: string[] = [];
  let moodEntries: EntryResponse[] = [];
  let inactiveTagIds: string[] = [];
  let detailView: DetailView = 'findings';
  let cooccurrenceRange: TagCooccurrenceRange = '30d';
  let cooccurrence: TagCooccurrenceResponse | null = null;
  let cooccurrenceLoading = false;
  let tagClusters: TagClustersResponse | null = null;
  let tagClustersLoading = false;
  let cooccurrenceHistoryOpen = false;
  let cooccurrenceHistoryTitle = '';
  let cooccurrenceHistoryLoading = false;
  let cooccurrenceHistoryError = '';
  let cooccurrenceHistoryDetails: EntryHistoryDetail[] = [];
  let symptomHistoryOpen = false;
  let symptomHistoryDate = '';
  let symptomHistoryLoading = false;
  let symptomHistoryError = '';
  let symptomHistoryDetails: EntryHistoryDetail[] = [];
  let symptomDetailOpen = false;
  let symptomDetailCell: SymptomTagCooccurrenceCell | null = null;
  let disclaimerOpen = false;
  let tagCooccurrenceSortMode: CooccurrenceSortMode = 'alphabetical';
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let symptomCooccurrence: SymptomTagCooccurrenceResponse | null = null;
  let symptomCooccurrenceLoading = false;
  let cooccurrenceRequested = false;
  let cooccurrenceRequestId = 0;
  let symptomCooccurrenceRequested = false;
  let symptomCooccurrenceRequestId = 0;
  let filterTab: InsightFeedFilterTab = 'all';
  let compactInsights = false;
  let mobileMedia: MediaQueryList | null = null;

  const analysisRangeOptions: { id: TimeseriesRange; label: string }[] = [
    { id: 'week', label: 'trends.range.week' },
    { id: 'month', label: 'trends.range.month' },
    { id: 'quarter', label: 'trends.range.quarter' },
    { id: 'year', label: 'trends.range.year' },
  ];

  $: cooccurrenceRange = timeseriesRangeToCooccurrence($analysisRange);

  let lastAnalysisRangeForCooccurrence: TimeseriesRange | null = null;
  $: if (
    $auth.status === 'authenticated' &&
    insightsLoaded &&
    $analysisRange !== lastAnalysisRangeForCooccurrence
  ) {
    const hadPrevious = lastAnalysisRangeForCooccurrence !== null;
    lastAnalysisRangeForCooccurrence = $analysisRange;
    if (hadPrevious && cooccurrenceRequested) {
      void loadCooccurrence();
    }
    if (hadPrevious && symptomCooccurrenceRequested) {
      void loadSymptomCooccurrence();
    }
  }

  $: analysisRangeControlOptions = analysisRangeOptions.map(
    (option): SegmentedControlOption => ({
      id: option.id,
      label: $_(option.label),
      testId: `insights-range-${option.id}`,
    })
  );

  $: filterTabOptions = getInsightFeedFilterTabs($_);

  async function loadCooccurrence(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    cooccurrenceRequested = true;
    const requestedRange = cooccurrenceRange;
    const requestId = ++cooccurrenceRequestId;
    cooccurrenceLoading = true;
    try {
      const nextCooccurrence = get(devForceVisualizations)
        ? mockTagCooccurrenceByRange[requestedRange]
        : await fetchTagCooccurrence({ range: requestedRange, min_count: 2 });
      if (requestId === cooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        cooccurrence = nextCooccurrence;
      }
    } catch {
      if (requestId === cooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        cooccurrence = null;
      }
    } finally {
      if (requestId === cooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        cooccurrenceLoading = false;
      }
    }
  }

  async function loadTagClusters(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    tagClustersLoading = true;
    try {
      if (get(devForceVisualizations)) {
        tagClusters = mockTagClusters;
        return;
      }
      tagClusters = await fetchTagClusters();
    } catch {
      tagClusters = null;
    } finally {
      tagClustersLoading = false;
    }
  }

  async function loadSymptomCooccurrence(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    symptomCooccurrenceRequested = true;
    const requestedRange = cooccurrenceRange;
    const requestId = ++symptomCooccurrenceRequestId;
    symptomCooccurrenceLoading = true;
    try {
      const nextSymptomCooccurrence = get(devForceVisualizations)
        ? mockSymptomTagCooccurrenceByRange[requestedRange]
        : await fetchSymptomTagCooccurrence({
            range: requestedRange,
            min_count: 3,
          });
      if (requestId === symptomCooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        symptomCooccurrence = nextSymptomCooccurrence;
      }
    } catch {
      if (requestId === symptomCooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        symptomCooccurrence = null;
      }
    } finally {
      if (requestId === symptomCooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        symptomCooccurrenceLoading = false;
      }
    }
  }

  async function openSymptomHistory(date: string): Promise<void> {
    symptomHistoryOpen = true;
    symptomHistoryDate = date;
    symptomHistoryLoading = true;
    symptomHistoryError = '';
    symptomHistoryDetails = [];
    try {
      if (get(devForceVisualizations)) {
        symptomHistoryDetails = mockEntries
          .filter((entry) => entry.entry_date === date)
          .map((entry) => ({
            entry,
            tags: ['Focus work'],
            symptoms: [{ name: 'Headache', intensity: 2 }],
          }));
        return;
      }

      const entries = await listEntries({ start_date: date, end_date: date, limit: 365 });
      const visibleSymptoms = await listVisibleSymptoms();
      const symptomNames = new Map(visibleSymptoms.map((symptom) => [symptom.id, symptom.name]));
      symptomHistoryDetails = await Promise.all(
        entries.map(async (entry: EntryResponse) => {
          const [tags, symptoms] = await Promise.all([
            listTagsForEntry(entry.id),
            listSymptomsForEntry(entry.id),
          ]);
          return {
            entry,
            tags: tags.map((tag) => tag.name),
            symptoms: symptoms.map((symptom) => ({
              name: symptomNames.get(symptom.symptom_id) ?? symptom.symptom_id,
              intensity: symptom.intensity,
            })),
          };
        })
      );
    } catch (err) {
      symptomHistoryError = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      symptomHistoryLoading = false;
    }
  }

  function openSymptomDetail(cell: SymptomTagCooccurrenceCell): void {
    symptomDetailCell = cell;
    symptomDetailOpen = true;
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
      if (get(devForceVisualizations)) {
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

  function bootstrapInsightsFromStore(): void {
    const cached = get(insightStore);
    if (cached.insights.length === 0) return;
    insights = cached.insights;
    insightMaturity = cached.insightMaturity;
  }

  async function loadInsights(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    loading = true;
    error = null;
    try {
      if (get(devForceVisualizations)) {
        insights = mockInsights;
        insightMaturity = mockInsightMaturity;
        userPreferences = mockUserPreferences;
        symptomHeatmap = mockSymptomHeatmap;
        symptomCooccurrence = mockSymptomTagCooccurrenceByRange[cooccurrenceRange];
        tagClusters = mockTagClusters;
        cooccurrence = mockTagCooccurrenceByRange[cooccurrenceRange];
        dayEntryDates = dayEntryDatesFromIsoEntries(mockEntries);
        moodEntries = mockEntries;
        entryCount = dayEntryDates.length;
        inactiveTagIds = [];
        return;
      }

      const todayIso = localIsoDate(new Date());
      const startIso = shiftIsoDate(todayIso, -89);
      const [
        insightsResult,
        entryResult,
        tagResult,
        defaultTagsResult,
        preferencesResult,
        symptomHeatmapResult,
      ] = await Promise.allSettled([
        listLatestInsights({ limit: 50 }),
        listEntries({ start_date: startIso, end_date: todayIso }),
        listVisibleTags({ include_hidden: true }),
        listDefaultTags(),
        fetchUserPreferences(),
        fetchSymptomHeatmap({ start_date: startIso, end_date: todayIso }),
      ]);

      if (insightsResult.status === 'fulfilled') {
        insights = insightsResult.value.insights;
        insightMaturity = insightsResult.value.insight_maturity;
      } else {
        const insightErr = insightsResult.reason;
        error = insightErr instanceof Error ? insightErr.message : $_('error.generic');
        if (insights.length === 0) {
          insightMaturity = null;
        }
      }

      userPreferences =
        preferencesResult.status === 'fulfilled' ? preferencesResult.value : userPreferences;
      symptomHeatmap =
        symptomHeatmapResult.status === 'fulfilled' ? symptomHeatmapResult.value : symptomHeatmap;

      if (entryResult.status === 'fulfilled') {
        dayEntryDates = dayEntryDatesFromIsoEntries(entryResult.value);
        moodEntries = entryResult.value;
        entryCount = dayEntryDates.length;
      }

      const tagResponse = tagResult.status === 'fulfilled' ? tagResult.value : [];
      const defaultTags = defaultTagsResult.status === 'fulfilled' ? defaultTagsResult.value : [];
      const inactiveSlugs = new Set(
        tagResponse.filter((tag) => tag.is_hidden).map((tag) => tag.slug)
      );
      inactiveTagIds = [
        ...tagResponse.filter((tag) => tag.is_hidden).map((tag) => tag.id),
        ...defaultTags.filter((tag) => inactiveSlugs.has(tag.slug)).map((tag) => tag.id),
      ];
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      if (insights.length === 0) {
        insightMaturity = null;
        userPreferences = null;
        symptomHeatmap = null;
        symptomCooccurrence = null;
        tagClusters = null;
        dayEntryDates = [];
        moodEntries = [];
        entryCount = 0;
        inactiveTagIds = [];
      }
    } finally {
      loading = false;
      insightsLoaded = true;
    }
  }

  $: feedLoading = loading || ($auth.status === 'authenticated' && !insightsLoaded);

  $: if ($auth.status === 'authenticated' && !insightsLoaded && !loading) {
    bootstrapInsightsFromStore();
    void loadInsights();
  }

  function syncCompactInsights(): void {
    compactInsights = mobileMedia?.matches ?? false;
  }

  onMount(() => {
    mobileMedia = window.matchMedia?.(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`) ?? null;
    syncCompactInsights();
    mobileMedia?.addEventListener('change', syncCompactInsights);

    return () => mobileMedia?.removeEventListener('change', syncCompactInsights);
  });

  $: showMaturityMilestone = shouldShowMaturityMilestone(
    insightMaturity,
    userPreferences?.reached_milestone_keys
  );
  $: showSymptomAnalytics =
    filterTab === 'symptoms' && (!insightMaturity || insightMaturity.phase !== 'collecting');
  $: matrixInsightCount = countMatrixInsights(insights);
  $: showMatrixTab = matrixInsightCount >= MATRIX_TAB_MIN_INSIGHTS;
  $: showAdvancedAnalytics = Boolean(insightMaturity && insightMaturity.phase !== 'collecting');
  $: if (!showMatrixTab && detailView === 'matrix') {
    detailView = 'findings';
  }
  $: filteredRankedInsights = rankedInsightsForTab(insights, filterTab);
  $: primaryMobileInsight = filteredRankedInsights[0] ?? null;
  $: remainingMobileInsights = filteredRankedInsights.slice(1);

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

  function handleAnalyticsToggle(event: Event): void {
    const open = event.currentTarget instanceof HTMLDetailsElement && event.currentTarget.open;
    if (!open) return;
    if (!cooccurrence && !cooccurrenceLoading) {
      void loadCooccurrence();
    }
    if (!tagClusters && !tagClustersLoading) {
      void loadTagClusters();
    }
    if (!symptomCooccurrence && !symptomCooccurrenceLoading) {
      void loadSymptomCooccurrence();
    }
  }
</script>

<svelte:head>
  <title>{$_('insights.page.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="insights-page screen-stack screen-stack--tight">
  <ScreenHeader title={$_('insights.page.title')} subtitle={$_('insights.page.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('insights.page.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">
        {$_('auth.login.submit')}
      </Button>
    </Panel>
  {:else}
    <div class="insights-page__sticky-toolbar" data-testid="insights-sticky-toolbar">
      <SegmentedControl
        value={$analysisRange}
        options={analysisRangeControlOptions}
        ariaLabel={$_('insights.page.analysis_range_label')}
        testId="insights-range-control"
        on:change={(event) => {
          setAnalysisRange(event.detail.value as TimeseriesRange);
        }}
      />
    </div>

    {#if !compactInsights && insightMaturity}
      <InsightStageHeader
        maturity={insightMaturity}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(e) => void dismissMaturityMilestone(e.detail.key)}
      />
    {/if}

    {#if compactInsights && detailView === 'findings' && !feedLoading && !error && primaryMobileInsight}
      <MobileInsightLead
        insight={primaryMobileInsight}
        maturity={insightMaturity}
        {entryCount}
        {inactiveTagIds}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
      />
    {:else if compactInsights && detailView === 'findings' && !feedLoading && !error && insightMaturity}
      <InsightStageHeader
        maturity={insightMaturity}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
      />
    {/if}

    {#if detailView === 'matrix'}
      <div class="insights-page__findings-toolbar" data-testid="insights-findings-toolbar">
        <button
          type="button"
          class="insights-page__view-link"
          data-testid="insights-findings-link"
          on:click={() => (detailView = 'findings')}
        >
          {$_('insights.page.findings_view')}
        </button>
      </div>
      <InsightMatrix {insights} />
    {:else}
      <div class="insights-page__findings-toolbar" data-testid="insights-findings-toolbar">
        <TabBar
          value={filterTab}
          options={filterTabOptions}
          ariaLabel={$_('insights.feed.filter_label')}
          testId="insights-filter-tabs"
          on:change={(event) => (filterTab = event.detail.value as InsightFeedFilterTab)}
        />
        {#if showMatrixTab}
          <button
            type="button"
            class="insights-page__view-link"
            data-testid="insights-matrix-link"
            on:click={() => (detailView = 'matrix')}
          >
            {$_('insights.page.matrix_view')}
          </button>
        {/if}
      </div>

      {#if compactInsights && primaryMobileInsight && remainingMobileInsights.length > 0 && !feedLoading && !error}
        <section class="insights-page__more" data-testid="mobile-insights-more">
          <h2>{$_('insights.mobile.more_heading')}</h2>
          <InsightFeed
            insights={remainingMobileInsights}
            maturity={insightMaturity}
            {entryCount}
            {inactiveTagIds}
            {filterTab}
            showContext={false}
            showFilters={false}
            on:retry={loadInsights}
          />
        </section>
      {:else if !compactInsights || !primaryMobileInsight || feedLoading || error}
        <InsightFeed
          {insights}
          maturity={insightMaturity}
          loading={feedLoading}
          {error}
          {entryCount}
          {inactiveTagIds}
          {filterTab}
          showFilters={false}
          on:retry={loadInsights}
        />
      {/if}
    {/if}

    {#if showAdvancedAnalytics}
      <details class="insights-page__analytics" on:toggle={handleAnalyticsToggle}>
        <summary>
          <span>{$_('insights.page.analytics_summary')}</span>
          <small>{$_('insights.page.analytics_hint')}</small>
        </summary>

        <div class="insights-page__analytics-body">
          {#if showSymptomAnalytics}
            <SymptomAnalyticsSection
              heatmap={symptomHeatmap}
              entries={moodEntries}
              cooccurrence={symptomCooccurrence}
              cooccurrenceLoading={symptomCooccurrenceLoading}
              phase={insightMaturity?.phase ?? null}
              {loading}
              on:selectDate={(event) => void openSymptomHistory(event.detail.date)}
              on:selectCell={(event) => openSymptomDetail(event.detail.cell)}
            />
          {/if}

          <TagGroupsSection data={tagClusters} loading={tagClustersLoading} />

          <TagCooccurrenceHeatmap
            data={cooccurrence}
            loading={cooccurrenceLoading}
            range={cooccurrenceRange}
            showRangeSelector={false}
            sortMode={tagCooccurrenceSortMode}
            enableClusterSort={insightMaturity?.phase === 'robust'}
            on:sortModeChange={(event) => (tagCooccurrenceSortMode = event.detail.sortMode)}
            on:selectPair={(event) => void openCooccurrenceHistory(event)}
          />
        </div>
      </details>
    {/if}

    <CooccurrenceEntrySheet
      open={cooccurrenceHistoryOpen}
      title={cooccurrenceHistoryTitle}
      loading={cooccurrenceHistoryLoading}
      error={cooccurrenceHistoryError}
      details={cooccurrenceHistoryDetails}
      on:close={() => (cooccurrenceHistoryOpen = false)}
    />

    <EntryHistorySheet
      open={symptomHistoryOpen}
      date={symptomHistoryDate}
      loading={symptomHistoryLoading}
      error={symptomHistoryError}
      details={symptomHistoryDetails}
      on:close={() => (symptomHistoryOpen = false)}
    />

    <SymptomCooccurrenceDetailSheet
      open={symptomDetailOpen}
      cell={symptomDetailCell}
      on:close={() => (symptomDetailOpen = false)}
      on:openDisclaimer={() => {
        symptomDetailOpen = false;
        disclaimerOpen = true;
      }}
    />

    <CorrelationDisclaimer open={disclaimerOpen} on:close={() => (disclaimerOpen = false)} />
  {/if}
</main>

<style>
  .insights-page {
    display: flex;
    flex-direction: column;
  }

  .insights-page__sticky-toolbar {
    position: sticky;
    top: calc(var(--app-header-height, 0px) + var(--space-2));
    z-index: 3;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 94%, transparent);
    backdrop-filter: blur(14px);
  }

  @media (max-width: 640px) {
    .insights-page__sticky-toolbar {
      position: static;
    }
  }

  .insights-page__analytics {
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .insights-page__analytics summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    min-height: 44px;
    padding: var(--space-3) var(--space-4);
    cursor: pointer;
    font-weight: 700;
  }

  .insights-page__analytics summary small {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 500;
    text-align: right;
  }

  .insights-page__analytics-body {
    display: grid;
    gap: var(--space-4);
    padding: 0 var(--space-4) var(--space-4);
    min-width: 0;
    overflow-x: clip;
  }

  .insights-page__findings-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .insights-page__view-link {
    min-height: 44px;
    border: 1px solid color-mix(in srgb, var(--color-primary) 25%, transparent);
    border-radius: var(--radius-full);
    padding: var(--space-2) var(--space-3);
    color: var(--color-primary);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    background: var(--color-primary-highlight);
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive),
      color var(--transition-interactive);
  }

  .insights-page__view-link:hover,
  .insights-page__view-link:focus-visible {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-primary-highlight) 80%, var(--color-surface));
  }

  .insights-page__more {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .insights-page__more h2 {
    margin: 0;
    font-size: var(--text-lg);
  }

  @media (max-width: 420px) {
    .insights-page__analytics summary {
      align-items: flex-start;
      flex-direction: column;
    }

    .insights-page__analytics summary small {
      text-align: left;
    }
  }
</style>
