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
   * InsightMatrix (M3.1 Step 4 / TODO-5) is rendered above the top insight
   * to show the unified correlation matrix for pointbiserial insights.
   */
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { dismissInsight, undismissInsight, insightStore } from '$lib/stores/insights';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';
  import { scheduleSync } from '$lib/offline/syncOrchestrator';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { fetchSymptomHeatmap, type SymptomHeatmapResponse } from '$lib/api/stats';
  import { ApiError } from '$lib/api/client';
  import {
    fetchInsightEventWindows,
    fetchSymptomTagCooccurrence,
    fetchTagClusters,
    fetchTagCooccurrence,
    listInsightDismissals,
    listLatestInsights,
    regenerateInsights,
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
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import DismissedInsightsSection, {
    type DismissedInsightItem,
  } from '$lib/components/insights/DismissedInsightsSection.svelte';
  import InsightsAnalysisToolbar from '$lib/components/insights/InsightsAnalysisToolbar.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import LagCorrelationHeatmap from '$lib/components/insights/LagCorrelationHeatmap.svelte';
  import { buildLagHeatmapRows } from '$lib/utils/lagHeatmap';
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
  import EventAlignedSmallMultiplesSheet from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import type { EventWindow } from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import type { CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';
  import { buildTagClusterMeta } from '$lib/utils/tagCooccurrenceMatrix';
  import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { analysisRange, setAnalysisRange } from '$lib/stores/analysisRange';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { shouldShowMaturityMilestone } from '$lib/utils/insightMaturityMilestones';
  import {
    getInsightFeedFilterTabs,
    rankedInsightsForTab,
    type InsightFeedFilterTab,
  } from '$lib/utils/insightFeedFilter';
  import {
    canShowAdvancedAnalytics,
    canShowMatrixTab,
    canShowTagCooccurrence,
    hasTagCooccurrenceData,
  } from '$lib/utils/insightAnalyticsGate';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
  import AnalysisCrossLink from '$lib/components/analysis/AnalysisCrossLink.svelte';
  import { timeseriesRangeToCooccurrence, analysisDateWindow } from '$lib/utils/analysisRange';
  import { rangeToDays } from '$lib/utils/trendsRange';
  import type { TimeseriesPoint, TimeseriesRange } from '$lib/api/stats';
  import type { MetricKey } from '$lib/utils/charts';
  import {
    devEventWindowsFromHeatmaps,
    devLagEventWindowsFromHeatmaps,
    insightMetricToChartKey,
  } from '$lib/utils/exploreEventWindows';
  import { isSmallMultiplesUnlocked } from '$lib/components/trends/smallMultiplesGate';

  let insights: InsightResponse[] = [];
  let dismissedItems: DismissedInsightItem[] = [];
  let loading = false;
  let insightsLoaded = false;
  let error: string | null = null;
  let insightMaturity: InsightMaturity | null = null;
  let userPreferences: UserPreferencesResponse | null = null;
  let regenerateBusy = false;
  let regenerateMessage = '';
  let regenerateError = '';
  let entryCount = 0;
  let dayEntryDates: string[] = [];
  let moodEntries: EntryResponse[] = [];
  let inactiveTagIds: string[] = [];
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
  let focusedTagClusterId: number | null = null;
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let symptomCooccurrence: SymptomTagCooccurrenceResponse | null = null;
  let symptomCooccurrenceLoading = false;
  let cooccurrenceRequested = false;
  let cooccurrenceRequestId = 0;
  let symptomCooccurrenceRequested = false;
  let symptomCooccurrenceRequestId = 0;
  let symptomWindowRequestId = 0;
  let symptomWindowLoading = false;
  let filterTab: InsightFeedFilterTab = 'all';
  let exploreEventsOpen = false;
  let exploreEventsInsight: InsightResponse | null = null;
  let exploreEventsWindows: EventWindow[] = [];
  let exploreEventsPoints: TimeseriesPoint[] = [];
  let exploreEventsMetric: MetricKey = 'mood_avg';
  let exploreEventsLagOffset: number | null = null;
  let exploreEventsLoading = false;
  let exploreEventsRequestId = 0;

  function readCompactInsights(): boolean {
    if (!browser) return false;
    return window.matchMedia(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`).matches;
  }

  let compactInsights = readCompactInsights();
  let mobileMedia: MediaQueryList | null = null;
  let activeDevFixtureKey = '';

  const analysisRangeOptions: { id: TimeseriesRange; label: string }[] = [
    { id: 'week', label: 'trends.range.week' },
    { id: 'month', label: 'trends.range.month' },
    { id: 'quarter', label: 'trends.range.quarter' },
    { id: 'year', label: 'trends.range.year' },
  ];

  $: insightsEffectiveRange =
    compactInsights && $analysisRange === 'year' ? 'quarter' : $analysisRange;
  $: cooccurrenceRange = timeseriesRangeToCooccurrence(insightsEffectiveRange);
  $: tagClusterMeta = buildTagClusterMeta(tagClusters);
  $: analysisRangeDays = rangeToDays(insightsEffectiveRange);
  $: toolbarAnalysisRange =
    compactInsights && $analysisRange === 'year' ? 'quarter' : $analysisRange;
  $: symptomWindowDataMatchesRange = symptomWindowDataRange === insightsEffectiveRange;
  $: visibleEntryCount = symptomWindowDataMatchesRange ? entryCount : 0;
  $: visibleMoodEntries = symptomWindowDataMatchesRange ? moodEntries : [];
  $: visibleSymptomHeatmap = symptomWindowDataMatchesRange ? symptomHeatmap : null;

  let lastAnalysisRangeForCooccurrence: TimeseriesRange | null = null;
  let lastAnalysisRangeForSymptomData: TimeseriesRange | null = null;
  let symptomWindowDataRange: TimeseriesRange | null = null;

  function cooccurrenceApiRangeFor(timeseriesRange: TimeseriesRange): TagCooccurrenceRange {
    return timeseriesRangeToCooccurrence(timeseriesRange);
  }

  function insightsRangeForData(range: TimeseriesRange = get(analysisRange)): TimeseriesRange {
    return compactInsights && range === 'year' ? 'quarter' : range;
  }

  function clearSymptomWindowData(): void {
    dayEntryDates = [];
    moodEntries = [];
    entryCount = 0;
    symptomHeatmap = null;
    symptomWindowDataRange = null;
  }

  function applySymptomWindowData(
    entries: EntryResponse[],
    heatmap: SymptomHeatmapResponse,
    range: TimeseriesRange
  ): void {
    dayEntryDates = dayEntryDatesFromIsoEntries(entries);
    moodEntries = entries;
    entryCount = dayEntryDates.length;
    symptomHeatmap = heatmap;
    lastAnalysisRangeForSymptomData = range;
    symptomWindowDataRange = range;
  }

  async function reloadSymptomWindowData(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    const requestedRange = insightsRangeForData();
    const requestId = ++symptomWindowRequestId;
    const { start_date, end_date } = analysisDateWindow(requestedRange);
    clearSymptomWindowData();
    lastAnalysisRangeForSymptomData = requestedRange;
    symptomWindowLoading = true;
    try {
      if (get(devForceVisualizations)) {
        const fixture = getDevPhaseFixture(get(devPhase));
        applySymptomWindowData(fixture.entries, fixture.symptomHeatmap, requestedRange);
        return;
      }

      const [entries, heatmap] = await Promise.all([
        listEntries({ start_date, end_date }),
        fetchSymptomHeatmap({ start_date, end_date }),
      ]);
      if (requestId !== symptomWindowRequestId || requestedRange !== insightsRangeForData()) return;
      applySymptomWindowData(entries, heatmap, requestedRange);
    } catch {
      // Keep the current range empty rather than mixing entries and heatmap from different windows.
    } finally {
      if (requestId === symptomWindowRequestId) {
        symptomWindowLoading = false;
      }
    }
  }

  $: if (
    $auth.status === 'authenticated' &&
    insightsEffectiveRange !== lastAnalysisRangeForCooccurrence
  ) {
    const previousRange = lastAnalysisRangeForCooccurrence;
    const nextRange = insightsEffectiveRange;
    lastAnalysisRangeForCooccurrence = nextRange;

    if (previousRange !== null) {
      const previousApiRange = cooccurrenceApiRangeFor(previousRange);
      const nextApiRange = cooccurrenceApiRangeFor(nextRange);
      const apiWindowChanged = previousApiRange !== nextApiRange;

      if (apiWindowChanged && (cooccurrenceRequested || cooccurrenceLoading)) {
        void loadCooccurrence();
      }
      if (apiWindowChanged && (symptomCooccurrenceRequested || symptomCooccurrenceLoading)) {
        void loadSymptomCooccurrence();
      }
      if (get(devForceVisualizations) && showAdvancedAnalytics) {
        void loadCooccurrence();
        void loadSymptomCooccurrence();
      }
    }
  }

  $: if (
    $auth.status === 'authenticated' &&
    insightsLoaded &&
    insightsEffectiveRange !== lastAnalysisRangeForSymptomData
  ) {
    void reloadSymptomWindowData();
  }

  $: visibleAnalysisRangeOptions = compactInsights
    ? analysisRangeOptions.filter((option) => option.id !== 'year')
    : analysisRangeOptions;
  $: analysisRangeControlOptions = visibleAnalysisRangeOptions.map((option) => ({
    id: option.id,
    label: $_(option.label),
    testId: `insights-range-${option.id}`,
  }));

  $: filterTabOptions = getInsightFeedFilterTabs($_);

  function devFixtureKey(): string {
    return `${$devPhase.presetId}:${$devPhase.entryCount}:${$devPhase.onboardingCompleted}`;
  }

  async function loadCooccurrence(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    cooccurrenceRequested = true;
    const requestedRange = cooccurrenceRange;
    const requestId = ++cooccurrenceRequestId;
    cooccurrenceLoading = true;
    try {
      const nextCooccurrence = get(devForceVisualizations)
        ? getDevPhaseFixture(get(devPhase)).tagCooccurrenceByRange[requestedRange]
        : await fetchTagCooccurrence({ range: requestedRange, min_count: 2 });
      if (requestId === cooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        cooccurrence = nextCooccurrence;
      }
    } catch {
      if (requestId === cooccurrenceRequestId && requestedRange === cooccurrenceRange) {
        cooccurrence = null;
      }
    } finally {
      if (requestId === cooccurrenceRequestId) {
        cooccurrenceLoading = false;
      }
    }
  }

  async function loadTagClusters(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    tagClustersLoading = true;
    try {
      if (get(devForceVisualizations)) {
        tagClusters = getDevPhaseFixture(get(devPhase)).tagClusters;
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
        ? getDevPhaseFixture(get(devPhase)).symptomTagCooccurrenceByRange[requestedRange]
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
      if (requestId === symptomCooccurrenceRequestId) {
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
        const fixture = getDevPhaseFixture(get(devPhase));
        symptomHistoryDetails = fixture.entries
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
        const fixture = getDevPhaseFixture(get(devPhase));
        cooccurrenceHistoryDetails = fixture.entries
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

  async function handleRegenerateInsights(): Promise<void> {
    if (userPreferences?.analytics_enabled === false) {
      regenerateError = $_('settings.analysis.regenerate_disabled');
      regenerateMessage = '';
      return;
    }
    regenerateBusy = true;
    regenerateMessage = '';
    regenerateError = '';
    try {
      const result = await regenerateInsights();
      regenerateMessage = $_('settings.analysis.regenerate_success', {
        values: { count: result.insight_count },
      });
      await loadInsights();
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        regenerateError = $_('settings.analysis.regenerate_rate_limited');
      } else if (err instanceof ApiError && err.status === 403) {
        regenerateError = $_('settings.analysis.regenerate_disabled');
      } else {
        regenerateError =
          err instanceof Error ? err.message : $_('settings.analysis.regenerate_error');
      }
    } finally {
      regenerateBusy = false;
    }
  }

  async function handleDismissInsight(id: string): Promise<void> {
    const dismissed = insights.find((insight) => insight.id === id);
    insights = insights.filter((insight) => insight.id !== id);
    const dismissal = await dismissInsight(id);
    if (dismissed) {
      const dismissalId = dismissal?.id ?? id;
      dismissedItems = [
        { dismissalId, insight: dismissed },
        ...dismissedItems.filter((item) => item.insight.id !== id),
      ];
    }
  }

  async function handleUndismissInsight(id: string, _dismissalId: string): Promise<void> {
    const restored = dismissedItems.find((item) => item.insight.id === id)?.insight;
    dismissedItems = dismissedItems.filter((item) => item.insight.id !== id);
    if (restored && !insights.some((insight) => insight.id === id)) {
      insights = [restored, ...insights];
    }
    await undismissInsight(id);
  }

  async function loadDismissedItems(): Promise<DismissedInsightItem[]> {
    try {
      const response = await listInsightDismissals();
      const items: DismissedInsightItem[] = [];
      for (const dismissal of response.dismissals) {
        if (!dismissal.insight) continue;
        items.push({ dismissalId: dismissal.id, insight: dismissal.insight });
      }
      return items;
    } catch {
      return [];
    }
  }

  async function loadInsights(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    loading = true;
    error = null;
    try {
      const requestedAnalysisRange = insightsRangeForData();
      if (get(devForceVisualizations)) {
        const fixture = getDevPhaseFixture(get(devPhase));
        activeDevFixtureKey = devFixtureKey();
        insights = fixture.insights;
        dismissedItems = [];
        insightMaturity = fixture.maturity;
        userPreferences = fixture.preferences;
        symptomHeatmap = fixture.symptomHeatmap;
        symptomCooccurrence = fixture.symptomTagCooccurrenceByRange[cooccurrenceRange];
        tagClusters = fixture.tagClusters;
        cooccurrence = fixture.tagCooccurrenceByRange[cooccurrenceRange];
        applySymptomWindowData(fixture.entries, fixture.symptomHeatmap, requestedAnalysisRange);
        inactiveTagIds = [];
        return;
      }

      const { start_date: startIso, end_date: todayIso } =
        analysisDateWindow(requestedAnalysisRange);
      const [insightsResult, symptomWindowResult, tagResult, defaultTagsResult, preferencesResult] =
        await Promise.allSettled([
          listLatestInsights({ limit: 50 }),
          Promise.all([
            listEntries({ start_date: startIso, end_date: todayIso }),
            fetchSymptomHeatmap({ start_date: startIso, end_date: todayIso }),
          ]),
          listVisibleTags({ include_hidden: true }),
          listDefaultTags(),
          fetchUserPreferences(),
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

      if (requestedAnalysisRange === insightsRangeForData()) {
        if (symptomWindowResult.status === 'fulfilled') {
          const [entries, heatmap] = symptomWindowResult.value;
          applySymptomWindowData(entries, heatmap, requestedAnalysisRange);
        } else if (lastAnalysisRangeForSymptomData !== requestedAnalysisRange) {
          clearSymptomWindowData();
          lastAnalysisRangeForSymptomData = requestedAnalysisRange;
        }
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
      const analyticsExcludedSlugs = new Set(
        tagResponse.filter((tag) => !tag.include_in_analytics).map((tag) => tag.slug)
      );
      const analyticsExcludedIds = new Set([
        ...tagResponse.filter((tag) => !tag.include_in_analytics).map((tag) => tag.id),
        ...defaultTags.filter((tag) => analyticsExcludedSlugs.has(tag.slug)).map((tag) => tag.id),
      ]);
      if (analyticsExcludedIds.size > 0 || analyticsExcludedSlugs.size > 0) {
        insights = insights.filter((insight) => {
          if (insight.subject_type !== 'tag') return true;
          if (insight.subject_id && analyticsExcludedIds.has(insight.subject_id)) return false;
          const slug = insight.payload?.tag_slug;
          if (typeof slug === 'string' && analyticsExcludedSlugs.has(slug)) return false;
          return true;
        });
      }
      const dismissedKeys = userPreferences?.dismissed_insight_keys ?? [];
      // Active feed is filtered server-side on /latest; keep a local guard for race safety.
      if (dismissedKeys.length > 0) {
        const dismissedSet = new Set(dismissedKeys);
        insights = insights.filter((insight) => !dismissedSet.has(insight.id));
      }
      dismissedItems = await loadDismissedItems();
      const dismissedInsightIds = new Set(dismissedItems.map((item) => item.insight.id));
      if (dismissedInsightIds.size > 0) {
        insights = insights.filter((insight) => !dismissedInsightIds.has(insight.id));
      }
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      if (insights.length === 0) {
        insightMaturity = null;
        userPreferences = null;
        dismissedItems = [];
        symptomCooccurrence = null;
        tagClusters = null;
        clearSymptomWindowData();
        inactiveTagIds = [];
      }
    } finally {
      loading = false;
      insightsLoaded = true;
    }
  }

  $: feedLoading = loading && insights.length === 0;

  $: if ($auth.status === 'authenticated' && !insightsLoaded && !loading) {
    bootstrapInsightsFromStore();
    void loadInsights();
  }

  $: if (
    $auth.status === 'authenticated' &&
    $devForceVisualizations &&
    insightsLoaded &&
    !loading &&
    activeDevFixtureKey !== devFixtureKey()
  ) {
    void loadInsights();
  }

  function syncCompactInsights(): void {
    compactInsights = readCompactInsights();
  }

  onMount(() => {
    mobileMedia = window.matchMedia?.(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`) ?? null;
    syncCompactInsights();
    mobileMedia?.addEventListener('change', syncCompactInsights);

    const unregisterRefresh = registerPageRefresh(async () => {
      await loadInsights();
      const reloads: Promise<void>[] = [];
      if (cooccurrenceRequested || cooccurrenceLoading) reloads.push(loadCooccurrence());
      if (symptomCooccurrenceRequested || symptomCooccurrenceLoading) {
        reloads.push(loadSymptomCooccurrence());
      }
      if (tagClusters || tagClustersLoading) reloads.push(loadTagClusters());
      if (reloads.length > 0) await Promise.all(reloads);
      scheduleSync();
    });

    return () => {
      unregisterRefresh();
      mobileMedia?.removeEventListener('change', syncCompactInsights);
    };
  });

  $: showMaturityMilestone = shouldShowMaturityMilestone(
    insightMaturity,
    userPreferences?.reached_milestone_keys
  );
  $: pageMaturityChrome = Boolean(insightMaturity);
  $: showSymptomAnalytics = canShowAdvancedAnalytics(insightMaturity?.phase ?? null);
  // #571: the correlation matrix is shown inline & prominent (not behind a tab).
  $: showMatrix = canShowMatrixTab(insightMaturity?.phase ?? null, insights);
  $: showAdvancedAnalytics = canShowAdvancedAnalytics(insightMaturity?.phase ?? null);
  // #488 Phase 2: only when advanced analytics are unlocked and ≥2 lag pairs carry a profile.
  $: showLagHeatmap = showAdvancedAnalytics && buildLagHeatmapRows(insights).length >= 2;
  $: showTagCooccurrencePanel =
    canShowTagCooccurrence(insightMaturity?.phase ?? null) &&
    (cooccurrenceLoading || hasTagCooccurrenceData(cooccurrence));
  $: filteredRankedInsights = rankedInsightsForTab(insights, filterTab);
  $: primaryMobileInsight = filteredRankedInsights[0] ?? null;
  $: remainingMobileInsights = filteredRankedInsights.slice(1);
  $: feedInsights =
    compactInsights && primaryMobileInsight ? remainingMobileInsights : filteredRankedInsights;
  $: showInsightFeed =
    feedInsights.length > 0 ||
    feedLoading ||
    Boolean(error) ||
    !compactInsights ||
    !primaryMobileInsight;
  $: enableExploreEvents = isSmallMultiplesUnlocked(insightMaturity?.phase ?? null);

  function ensureAnalyticsLoaded(): void {
    if (!cooccurrenceRequested && !cooccurrenceLoading) {
      void loadCooccurrence();
    }
    if (!tagClusters && !tagClustersLoading) {
      void loadTagClusters();
    }
    if (!symptomCooccurrenceRequested && !symptomCooccurrenceLoading) {
      void loadSymptomCooccurrence();
    }
  }

  $: if (showAdvancedAnalytics && $auth.status === 'authenticated' && insightsLoaded) {
    ensureAnalyticsLoaded();
  }

  async function openExploreEvents(insightId: string): Promise<void> {
    const insight =
      insights.find((row) => row.id === insightId) ??
      (primaryMobileInsight?.id === insightId ? primaryMobileInsight : null);
    if (!insight) return;

    const requestId = ++exploreEventsRequestId;

    exploreEventsInsight = insight;
    exploreEventsMetric = insightMetricToChartKey(insight.metric);
    exploreEventsOpen = true;
    exploreEventsLoading = true;
    exploreEventsWindows = [];
    exploreEventsPoints = [];
    exploreEventsLagOffset = null;

    try {
      const range = insightsEffectiveRange;
      if (get(devForceVisualizations)) {
        const fixture = getDevPhaseFixture(get(devPhase));
        if (requestId !== exploreEventsRequestId || exploreEventsInsight?.id !== insightId) {
          return;
        }
        exploreEventsWindows =
          insight.payload?.method === 'lag'
            ? devLagEventWindowsFromHeatmaps(insight, fixture.tagHeatmap, fixture.symptomHeatmap)
            : devEventWindowsFromHeatmaps(insight, fixture.tagHeatmap, fixture.symptomHeatmap);
        exploreEventsPoints = fixture.timeseries.points;
        const devLag = insight.payload?.lag_days;
        exploreEventsLagOffset = typeof devLag === 'number' ? devLag : null;
        return;
      }

      const response = await fetchInsightEventWindows(
        insight.id,
        timeseriesRangeToCooccurrence(range)
      );
      if (requestId !== exploreEventsRequestId || exploreEventsInsight?.id !== insightId) {
        return;
      }
      exploreEventsWindows = response.events.map((event) => ({
        onset: event.onset,
        label: event.label ?? undefined,
      }));
      exploreEventsPoints = response.points;
      exploreEventsLagOffset = response.lag_days ?? null;
    } catch {
      if (requestId !== exploreEventsRequestId || exploreEventsInsight?.id !== insightId) {
        return;
      }
      exploreEventsWindows = [];
      exploreEventsPoints = [];
      exploreEventsLagOffset = null;
    } finally {
      if (requestId === exploreEventsRequestId && exploreEventsInsight?.id === insightId) {
        exploreEventsLoading = false;
      }
    }
  }

  async function dismissMaturityMilestone(key: string): Promise<void> {
    const reached = new Set(userPreferences?.reached_milestone_keys ?? []);
    reached.add(key);
    const optimistic = {
      ...(userPreferences ?? {
        user_id: '',
        analytics_enabled: true,
        digest_enabled: true,
        onboarding_retro_completed: false,
        onboarding_profile_completed: false,
        onboarding_maturity_intro_seen: false,
        cycle_tracking_enabled: true,
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

<main class="insights-page screen-stack screen-stack--tight">
  <ScreenHeader title={$_('insights.page.title')} subtitle={$_('insights.page.subtitle')} />
  <p class="insights-page__history-link">
    <a href="/insights/history">{$_('insights.page.history_link')}</a>
  </p>

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('insights.page.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">
        {$_('auth.login.submit')}
      </Button>
    </Panel>
  {:else}
    <InsightsAnalysisToolbar
      analysisRange={toolbarAnalysisRange}
      analysisRangeOptions={analysisRangeControlOptions}
      {filterTab}
      {filterTabOptions}
      on:rangeChange={(event) => setAnalysisRange(event.detail.value)}
      on:filterChange={(event) => (filterTab = event.detail.value)}
    />

    {#if showMatrix}
      <section class="insights-page__matrix" data-testid="insights-matrix-section">
        <InsightMatrix {insights} />
      </section>
    {/if}

    {#if !compactInsights && insightMaturity}
      <InsightStageHeader
        maturity={insightMaturity}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(e) => void dismissMaturityMilestone(e.detail.key)}
      />
    {/if}

    {#if compactInsights && !feedLoading && !error && primaryMobileInsight}
      <MobileInsightLead
        insight={primaryMobileInsight}
        maturity={insightMaturity}
        entryCount={visibleEntryCount}
        {inactiveTagIds}
        showMilestone={showMaturityMilestone}
        {enableExploreEvents}
        on:dismiss={(event) => void handleDismissInsight(event.detail.id)}
        on:exploreEvents={(event) => void openExploreEvents(event.detail.id)}
        on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
      />
    {:else if compactInsights && !feedLoading && !error && insightMaturity}
      <InsightStageHeader
        maturity={insightMaturity}
        showMilestone={showMaturityMilestone}
        on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
      />
    {/if}

    {#if showLagHeatmap}
      <section class="insights-page__lag-heatmap" data-testid="insights-lag-heatmap-section">
        <LagCorrelationHeatmap {insights} />
      </section>
    {/if}

    {#if !compactInsights && primaryMobileInsight}
      <AnalysisCrossLink insight={primaryMobileInsight} direction="to-trends" />
    {/if}

    {#if showInsightFeed}
      {#if compactInsights && feedInsights.length > 0 && primaryMobileInsight}
        <section class="insights-page__more" data-testid="mobile-insights-more">
          <h2>{$_('insights.mobile.more_heading')}</h2>
          <InsightFeed
            insights={feedInsights}
            totalInsightCount={insights.length}
            maturity={insightMaturity}
            entryCount={visibleEntryCount}
            {analysisRangeDays}
            {inactiveTagIds}
            {filterTab}
            {enableExploreEvents}
            {regenerateBusy}
            {regenerateMessage}
            {regenerateError}
            showContext={false}
            showFilters={false}
            showMaturityBadge={false}
            on:retry={loadInsights}
            on:regenerate={() => void handleRegenerateInsights()}
            on:dismiss={(event) => void handleDismissInsight(event.detail.id)}
            on:exploreEvents={(event) => void openExploreEvents(event.detail.id)}
            on:selectDate={(event) => void openSymptomHistory(event.detail.date)}
          />
        </section>
      {:else}
        <InsightFeed
          insights={feedInsights}
          totalInsightCount={insights.length}
          maturity={insightMaturity}
          loading={feedLoading}
          {error}
          entryCount={visibleEntryCount}
          {analysisRangeDays}
          {inactiveTagIds}
          {filterTab}
          {enableExploreEvents}
          {regenerateBusy}
          {regenerateMessage}
          {regenerateError}
          showFilters={false}
          showMaturityBadge={!pageMaturityChrome}
          on:retry={loadInsights}
          on:regenerate={() => void handleRegenerateInsights()}
          on:dismiss={(event) => void handleDismissInsight(event.detail.id)}
          on:exploreEvents={(event) => void openExploreEvents(event.detail.id)}
          on:selectDate={(event) => void openSymptomHistory(event.detail.date)}
        />
      {/if}
    {/if}

    <DismissedInsightsSection
      items={dismissedItems}
      maturity={insightMaturity}
      {inactiveTagIds}
      on:undismiss={(event) =>
        void handleUndismissInsight(event.detail.id, event.detail.dismissalId)}
    />

    {#if showAdvancedAnalytics}
      <section class="insights-page__analytics" data-testid="insights-analytics-panel">
        <header class="insights-page__analytics-header">
          <h2>{$_('insights.page.analytics_summary')}</h2>
          <p>{$_('insights.page.analytics_hint')}</p>
        </header>

        <div class="insights-page__analytics-body">
          {#if showSymptomAnalytics}
            <SymptomAnalyticsSection
              heatmap={visibleSymptomHeatmap}
              entries={visibleMoodEntries}
              cooccurrence={symptomCooccurrence}
              cooccurrenceLoading={symptomCooccurrenceLoading}
              phase={insightMaturity?.phase ?? null}
              loading={loading || symptomWindowLoading}
              pruneSparseAxes
              on:selectDate={(event) => void openSymptomHistory(event.detail.date)}
              on:selectCell={(event) => openSymptomDetail(event.detail.cell)}
            />
          {/if}

          <TagGroupsSection data={tagClusters} loading={tagClustersLoading} />

          {#if showTagCooccurrencePanel}
            <TagCooccurrenceHeatmap
              data={cooccurrence}
              loading={cooccurrenceLoading}
              range={cooccurrenceRange}
              showRangeSelector={false}
              sortMode={tagCooccurrenceSortMode}
              enableClusterSort={insightMaturity?.phase === 'robust'}
              clusterMeta={tagClusterMeta}
              bind:focusedClusterId={focusedTagClusterId}
              pruneSparseAxes
              on:sortModeChange={(event) => (tagCooccurrenceSortMode = event.detail.sortMode)}
              on:selectPair={(event) => void openCooccurrenceHistory(event)}
            />
          {/if}
        </div>
      </section>
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

    <EventAlignedSmallMultiplesSheet
      open={exploreEventsOpen && !exploreEventsLoading}
      events={exploreEventsWindows}
      points={exploreEventsPoints}
      metric={exploreEventsMetric}
      lagOffset={exploreEventsLagOffset}
      phase={exploreEventsInsight ? (insightMaturity?.phase ?? null) : null}
      on:close={() => {
        exploreEventsOpen = false;
        exploreEventsInsight = null;
      }}
    />
  {/if}
</main>

<style>
  .insights-page {
    display: flex;
    flex-direction: column;
  }

  /* #571: correlation matrix sits inline & prominent; keep wide content scrolling
     inside the matrix, not the page. */
  .insights-page__history-link {
    margin: 0;
    font-size: var(--text-sm);
  }

  .insights-page__matrix {
    min-width: 0;
    max-width: 100%;
  }

  .insights-page__analytics {
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    min-width: 0;
  }

  .insights-page__analytics-header {
    display: grid;
    gap: var(--space-1);
    padding: var(--space-4) var(--space-4) 0;
  }

  .insights-page__analytics-header h2,
  .insights-page__analytics-header p {
    margin: 0;
  }

  .insights-page__analytics-header h2 {
    font-size: var(--text-lg);
  }

  .insights-page__analytics-header p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .insights-page__analytics-body {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-4);
    padding: var(--space-4);
    min-width: 0;
    max-width: 100%;
    /* Keep horizontal scroll inside each chart/heatmap — not the shared panel. */
    overflow-x: hidden;
  }

  .insights-page__analytics-body > :global(*) {
    min-width: 0;
    max-width: 100%;
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
</style>
