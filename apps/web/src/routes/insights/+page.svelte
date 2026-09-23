<script lang="ts">
  /**
   * /insights — InsightFeed page (M3.1, Issue #164)
   *
   * Replaces the old raw-list rendering with the InsightFeed component.
   * - Sort: confidence × |effect_size| descending (done inside InsightFeed)
   * - Inline error banner — no full-page crash on API failure
   * - Empty state / skeleton delegated to InsightFeed
   *
   * InsightMatrix (M3.1 Step 4 / TODO-5) is rendered above the top insight
   * to show the unified correlation matrix for pointbiserial insights.
   */
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { dismissInsight, undismissInsight, insightStore } from '$lib/stores/insights';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';
  import { scheduleSync } from '$lib/offline/syncOrchestrator';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import {
    fetchSymptomHeatmap,
    fetchTagHeatmap,
    type SymptomHeatmapResponse,
    type TagHeatmapResponse,
  } from '$lib/api/stats';
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
  import {
    INSIGHT_TOOL_SECTION_KEYS,
    mergeInsightSections,
    resolveEnabledInsightSections,
  } from '$lib/utils/insightSections';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightFeed from '$lib/components/insights/InsightFeed.svelte';
  import DismissedInsightsSection from '$lib/components/insights/DismissedInsightsSection.svelte';
  import type { DismissedInsightItem } from '$lib/components/insights/dismissedInsights';
  import InsightsAnalysisToolbar from '$lib/components/insights/InsightsAnalysisToolbar.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import LagCorrelationHeatmap from '$lib/components/insights/LagCorrelationHeatmap.svelte';
  import { buildLagHeatmapRows } from '$lib/utils/lagHeatmap';
  import InsightStageHeader from '$lib/components/insights/InsightStageHeader.svelte';
  import BelastungOverlay from '$lib/components/insights/BelastungOverlay.svelte';
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
  import { localIsoDate } from '$lib/utils/isoDate';
  import {
    coerceTrendWindowDays,
    trendWindowDaysToTimeseriesRange,
    type TrendWindowDays,
  } from '$lib/utils/trendWindowDays';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { shouldShowMaturityMilestone } from '$lib/utils/insightMaturityMilestones';
  import { rankInsights } from '$lib/utils/insightRanking';
  import {
    canShowAdvancedAnalytics,
    canShowMatrixTab,
    canShowTagCooccurrence,
    hasTagCooccurrenceData,
  } from '$lib/utils/insightAnalyticsGate';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
  import AnalysisCrossLink from '$lib/components/analysis/AnalysisCrossLink.svelte';
  import { timeseriesRangeToCooccurrence } from '$lib/utils/analysisRange';
  import { shiftIsoDate } from '$lib/utils/isoDate';
  import type { TimeseriesPoint } from '$lib/api/stats';
  import type { MetricKey } from '$lib/utils/charts';
  import {
    devEventWindowsFromHeatmaps,
    devLagEventWindowsFromHeatmaps,
    insightMetricToChartKey,
  } from '$lib/utils/exploreEventWindows';
  import {
    candidatesFromSymptomTagCooccurrence,
    candidatesFromTagCooccurrence,
    clampPartnerCandidates,
    pickDefaultPartner,
    presenceDatesForPartner,
    resolveEsmAlignSubject,
    type EsmPartner,
    type EsmPartnerCandidate,
  } from '$lib/utils/esmPartner';
  import {
    analysisPairQuery,
    insightMatchesAnalysisPair,
    parseAnalysisPair,
    partnerForInsight,
    type AnalysisSignalRef,
  } from '$lib/utils/analysisPairHandoff';
  import { buildWorkContextHeatmap } from '$lib/utils/workContextHeatmap';
  import {
    isSmallMultiplesUnlocked,
    SMALL_MULTIPLES_RADIUS,
  } from '$lib/components/trends/smallMultiplesGate';

  let insights: InsightResponse[] = [];
  let dismissedItems: DismissedInsightItem[] = [];
  let showDismissedPanel = false;
  let loading = false;
  let insightsLoaded = false;
  let carriedPairInsights: InsightResponse[] = [];
  let carriedPairLookupComplete = false;
  let error: string | null = null;
  let insightMaturity: InsightMaturity | null = null;
  let lastSuccessfulInsightRunAt: string | null = null;
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
  let exploreEventsOpen = false;
  let exploreEventsInsight: InsightResponse | null = null;
  let exploreEventsWindows: EventWindow[] = [];
  let exploreEventsPoints: TimeseriesPoint[] = [];
  let exploreEventsMetric: MetricKey = 'mood_avg';
  let exploreEventsLagOffset: number | null = null;
  let exploreEventsLoading = false;
  let exploreEventsRequestId = 0;
  let exploreEventsPartner: EsmPartner | null = null;
  let exploreEventsPartnerCandidates: EsmPartnerCandidate[] = [];
  let exploreEventsPartnerPresence: string[] = [];
  let exploreEventsTagHeatmap: TagHeatmapResponse | null = null;
  let exploreEventsSymptomHeatmap: SymptomHeatmapResponse | null = null;
  let exploreEventsWorkContextHeatmap: ReturnType<typeof buildWorkContextHeatmap> | null = null;
  // #918: the sheet opens before partner data arrives — keep "still loading"
  // and "presence data failed" apart from "no partner exists".
  let exploreEventsPartnerLoading = false;
  let exploreEventsPartnerUnavailable = false;

  function readCompactInsights(): boolean {
    if (!browser) return false;
    return window.matchMedia(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`).matches;
  }

  let compactInsights = readCompactInsights();
  let mobileMedia: MediaQueryList | null = null;
  let activeDevFixtureKey = '';

  const analysisRangeOptions: { id: string; label: string }[] = [
    { id: '14', label: 'trends.range.d14' },
    { id: '28', label: 'trends.range.d28' },
    { id: '90', label: 'trends.range.d90' },
  ];

  $: windowDays = $analysisRange;
  $: insightsEffectiveRange = trendWindowDaysToTimeseriesRange(windowDays);
  $: cooccurrenceRange = timeseriesRangeToCooccurrence(insightsEffectiveRange);
  $: tagClusterMeta = buildTagClusterMeta(tagClusters);
  $: analysisRangeDays = windowDays;
  $: symptomWindowDataMatchesRange = symptomWindowDataDays === windowDays;
  $: visibleEntryCount = symptomWindowDataMatchesRange ? entryCount : 0;
  $: visibleMoodEntries = symptomWindowDataMatchesRange ? moodEntries : [];
  $: visibleSymptomHeatmap = symptomWindowDataMatchesRange ? symptomHeatmap : null;
  $: analysisRangeControlOptions = analysisRangeOptions.map((option) => ({
    id: option.id,
    label: $_(option.label),
    testId: `insights-range-${option.id}`,
  }));

  let lastWindowDaysForCooccurrence: TrendWindowDays | null = null;
  let lastWindowDaysForSymptomData: TrendWindowDays | null = null;
  let symptomWindowDataDays: TrendWindowDays | null = null;

  function cooccurrenceApiRangeFor(days: TrendWindowDays): TagCooccurrenceRange {
    return timeseriesRangeToCooccurrence(trendWindowDaysToTimeseriesRange(days));
  }

  function trendWindowDateBounds(days: TrendWindowDays): { start_date: string; end_date: string } {
    const end_date = localIsoDate(new Date());
    return { start_date: shiftIsoDate(end_date, -(days - 1)), end_date };
  }

  function clearSymptomWindowData(): void {
    dayEntryDates = [];
    moodEntries = [];
    entryCount = 0;
    symptomHeatmap = null;
    symptomWindowDataDays = null;
  }

  function applySymptomWindowData(
    entries: EntryResponse[],
    heatmap: SymptomHeatmapResponse,
    days: TrendWindowDays
  ): void {
    dayEntryDates = dayEntryDatesFromIsoEntries(entries);
    moodEntries = entries;
    entryCount = dayEntryDates.length;
    symptomHeatmap = heatmap;
    lastWindowDaysForSymptomData = days;
    symptomWindowDataDays = days;
  }

  async function reloadSymptomWindowData(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    const requestedDays = windowDays;
    const requestId = ++symptomWindowRequestId;
    const { start_date, end_date } = trendWindowDateBounds(requestedDays);
    clearSymptomWindowData();
    lastWindowDaysForSymptomData = requestedDays;
    symptomWindowLoading = true;
    try {
      if (get(devForceVisualizations)) {
        const fixture = getDevPhaseFixture(get(devPhase));
        applySymptomWindowData(fixture.entries, fixture.symptomHeatmap, requestedDays);
        return;
      }

      const [entries, heatmap] = await Promise.all([
        listEntries({ start_date, end_date }),
        fetchSymptomHeatmap({ start_date, end_date }),
      ]);
      if (requestId !== symptomWindowRequestId || requestedDays !== windowDays) return;
      applySymptomWindowData(entries, heatmap, requestedDays);
    } catch {
      // Keep the current range empty rather than mixing entries and heatmap from different windows.
    } finally {
      if (requestId === symptomWindowRequestId) {
        symptomWindowLoading = false;
      }
    }
  }

  $: if ($auth.status === 'authenticated' && windowDays !== lastWindowDaysForCooccurrence) {
    const previousDays = lastWindowDaysForCooccurrence;
    const nextDays = windowDays;
    lastWindowDaysForCooccurrence = nextDays;

    if (previousDays !== null) {
      const previousApiRange = cooccurrenceApiRangeFor(previousDays);
      const nextApiRange = cooccurrenceApiRangeFor(nextDays);
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
    windowDays !== lastWindowDaysForSymptomData
  ) {
    void reloadSymptomWindowData();
  }

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
            tags: fixture.tagsByEntryId[entry.id] ?? [],
            symptoms: fixture.symptomsByEntryId[entry.id] ?? [{ name: 'Headache', intensity: 2 }],
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

  async function handleUndismissInsight(id: string, dismissalId: string): Promise<void> {
    const restored = dismissedItems.find((item) => item.insight.id === id)?.insight;
    dismissedItems = dismissedItems.filter((item) => item.insight.id !== id);
    if (restored && !insights.some((insight) => insight.id === id)) {
      insights = [restored, ...insights];
    }
    await undismissInsight(id, { dismissalId });
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
    carriedPairInsights = [];
    carriedPairLookupComplete = false;
    try {
      const requestedDays = windowDays;
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
        applySymptomWindowData(fixture.entries, fixture.symptomHeatmap, requestedDays);
        inactiveTagIds = [];
        return;
      }

      const { start_date: startIso, end_date: todayIso } = trendWindowDateBounds(requestedDays);
      const requestedPair = parseAnalysisPair(get(page).url.searchParams);
      const [
        insightsResult,
        pairResult,
        symptomWindowResult,
        tagResult,
        defaultTagsResult,
        preferencesResult,
      ] = await Promise.allSettled([
        listLatestInsights({ limit: 50 }),
        requestedPair
          ? listLatestInsights({
              limit: 50,
              pairSignals: requestedPair.signals.map(({ kind, id }) => ({ kind, id })),
            })
          : Promise.resolve(null),
        Promise.all([
          listEntries({ start_date: startIso, end_date: todayIso }),
          fetchSymptomHeatmap({ start_date: startIso, end_date: todayIso }),
        ]),
        listVisibleTags({ include_hidden: true }),
        listDefaultTags(),
        fetchUserPreferences(),
      ]);

      if (requestedPair && pairResult.status === 'fulfilled' && pairResult.value) {
        carriedPairInsights = pairResult.value.insights;
        carriedPairLookupComplete = true;
      }

      if (insightsResult.status === 'fulfilled') {
        insights = insightsResult.value.insights;
        insightMaturity = insightsResult.value.insight_maturity;
        lastSuccessfulInsightRunAt = insightsResult.value.last_successful_insight_run_at ?? null;
      } else {
        const insightErr = insightsResult.reason;
        error = insightErr instanceof Error ? insightErr.message : $_('error.generic');
        if (insights.length === 0) {
          insightMaturity = null;
        }
      }

      userPreferences =
        preferencesResult.status === 'fulfilled' ? preferencesResult.value : userPreferences;

      if (requestedDays === windowDays) {
        if (symptomWindowResult.status === 'fulfilled') {
          const [entries, heatmap] = symptomWindowResult.value;
          applySymptomWindowData(entries, heatmap, requestedDays);
        } else if (lastWindowDaysForSymptomData !== requestedDays) {
          clearSymptomWindowData();
          lastWindowDaysForSymptomData = requestedDays;
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
    void fetchUserPreferences()
      .then((prefs) => analysisRange.hydrateFromServer(prefs.trend_window_days))
      .catch(() => {
        // Keep local cache when preferences are unavailable.
      });

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
  // #823: the readiness header is a configurable section now — when the user
  // hides it, the feed shows its own maturity badge so phase info is not lost.
  $: pageMaturityChrome = Boolean(insightMaturity) && stageHeaderEnabled;
  $: showSymptomAnalytics = canShowAdvancedAnalytics(insightMaturity?.phase ?? null);
  // #571: the correlation matrix is shown inline & prominent (not behind a tab).
  $: showMatrix = canShowMatrixTab(insightMaturity?.phase ?? null, insights);
  $: showAdvancedAnalytics = canShowAdvancedAnalytics(insightMaturity?.phase ?? null);
  // #488 Phase 2: only when advanced analytics are unlocked and ≥2 lag pairs carry a profile.
  $: showLagHeatmap = showAdvancedAnalytics && buildLagHeatmapRows(insights).length >= 2;
  $: showTagCooccurrencePanel =
    canShowTagCooccurrence(insightMaturity?.phase ?? null) &&
    (cooccurrenceLoading || hasTagCooccurrenceData(cooccurrence));
  /**
   * The Belastung composite has its own opt-in overlay, so it must not also ride
   * the ordinary feed: enabled users saw it twice, and users who switched the
   * opt-in back off kept seeing the stored rows as a regular insight, because
   * disabling a preference does not delete what the worker already wrote (#957).
   */
  $: rankableInsights = insights.filter((insight) => insight.insight_type !== 'belastung_pattern');
  $: carriedPair = parseAnalysisPair($page.url.searchParams);
  $: carriedPairQuery = carriedPair ? analysisPairQuery(carriedPair) : '';
  $: carriedMatches = carriedPair
    ? carriedPairInsights.filter((insight) => insightMatchesAnalysisPair(insight, carriedPair!))
    : [];
  $: carriedPairSearchComplete = Boolean(
    carriedPair && carriedPairLookupComplete && insightsLoaded && !loading && !error
  );
  $: carriedSignalsUnmatched = carriedPairSearchComplete && carriedMatches.length === 0;
  $: carriedPairFocused = carriedPairSearchComplete && carriedMatches.length > 0;
  $: focusedRankableInsights = carriedPairFocused ? carriedMatches : rankableInsights;
  $: filteredRankedInsights = rankInsights(focusedRankableInsights);
  $: primaryMobileInsight = filteredRankedInsights[0] ?? null;
  $: remainingMobileInsights = filteredRankedInsights.slice(1);
  /** Keep the structured Compare pair focused in the mobile lead and desktop feed. */
  $: feedInsights =
    compactInsights && primaryMobileInsight ? remainingMobileInsights : filteredRankedInsights;
  $: showInsightFeed =
    feedInsights.length > 0 ||
    feedLoading ||
    Boolean(error) ||
    !compactInsights ||
    Boolean(primaryMobileInsight);
  $: enableExploreEvents = isSmallMultiplesUnlocked(insightMaturity?.phase ?? null);

  // #821/#823: configurable section order/visibility. `insight_feed` is locked
  // (always enabled) but reorderable; the readiness `stage_header` is now a
  // regular section (hideable + reorderable). User config is an AND-gate on top
  // of the existing phase/data gates below.
  $: enabledInsightSectionKeys = resolveEnabledInsightSections(
    mergeInsightSections(userPreferences?.insight_sections ?? null)
  ).map((section) => section.key);
  $: stageHeaderEnabled = enabledInsightSectionKeys.includes('stage_header');
  $: dismissedSectionEnabled = enabledInsightSectionKeys.includes('dismissed');
  $: enabledSectionSet = new Set(enabledInsightSectionKeys);
  $: hiddenToolKeys = INSIGHT_TOOL_SECTION_KEYS.filter((key) => !enabledSectionSet.has(key));
  $: showToolsRow =
    hiddenToolKeys.length > 0 || (!dismissedSectionEnabled && dismissedItems.length > 0);
  // The milestone belongs to the stage_header section, so hiding that section
  // hides the milestone everywhere. On mobile-with-primary the milestone-only
  // strip lives inside MobileInsightLead (gated by showLeadMilestone), and the
  // standalone header suppresses its own copy there to avoid a duplicate.
  $: showLeadMilestone = showMaturityMilestone && stageHeaderEnabled;
  $: showStageMilestone =
    showMaturityMilestone && stageHeaderEnabled && !(compactInsights && primaryMobileInsight);
  $: belastungInsight =
    insights.find((insight) => insight.insight_type === 'belastung_pattern') ?? null;
  $: showBelastungOverlay =
    Boolean(userPreferences?.belastung_overlay_enabled) &&
    userPreferences?.analytics_enabled !== false &&
    Boolean(belastungInsight);

  /**
   * Load only what the hub is actually going to render.
   *
   * This used to fire all three requests for every user in an advanced maturity
   * phase, regardless of which sections were enabled. After the Phase 6 shrink
   * the optional tools are off by default, so the common case paid for
   * co-occurrence, tag-cluster and symptom-co-occurrence queries whose
   * components never mounted — exactly the cost that shrink set out to remove
   * (#957). Each load now follows its own section.
   */
  function ensureAnalyticsLoaded(): void {
    if (
      enabledSectionSet.has('tag_cooccurrence') &&
      !cooccurrenceRequested &&
      !cooccurrenceLoading
    ) {
      void loadCooccurrence();
    }
    if (enabledSectionSet.has('tag_groups') && !tagClusters && !tagClustersLoading) {
      void loadTagClusters();
    }
    if (
      enabledSectionSet.has('symptom_analytics') &&
      !symptomCooccurrenceRequested &&
      !symptomCooccurrenceLoading
    ) {
      void loadSymptomCooccurrence();
    }
  }

  // Re-runs when a section is switched on, so enabling a tool still loads it.
  $: if (
    showAdvancedAnalytics &&
    $auth.status === 'authenticated' &&
    insightsLoaded &&
    enabledSectionSet
  ) {
    ensureAnalyticsLoaded();
  }

  async function openExploreEvents(insightId: string): Promise<void> {
    const insight =
      insights.find((row) => row.id === insightId) ??
      (primaryMobileInsight?.id === insightId ? primaryMobileInsight : null);
    if (!insight) return;

    const requestId = ++exploreEventsRequestId;
    const capturedDays = windowDays;

    exploreEventsInsight = insight;
    exploreEventsMetric = insightMetricToChartKey(insight.metric);
    exploreEventsOpen = true;
    exploreEventsLoading = true;
    exploreEventsWindows = [];
    exploreEventsPoints = [];
    exploreEventsLagOffset = null;
    exploreEventsPartner = null;
    exploreEventsPartnerCandidates = [];
    exploreEventsPartnerPresence = [];
    exploreEventsPartnerLoading = false;
    exploreEventsPartnerUnavailable = false;
    exploreEventsTagHeatmap = null;
    exploreEventsSymptomHeatmap = null;
    exploreEventsWorkContextHeatmap = null;

    try {
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
        exploreEventsTagHeatmap = fixture.tagHeatmap;
        exploreEventsSymptomHeatmap = fixture.symptomHeatmap;
        const fixtureBounds = trendWindowDateBounds(capturedDays);
        exploreEventsWorkContextHeatmap = buildWorkContextHeatmap(fixture.entries, fixtureBounds);
        applyExploreEventsPartner(
          insight,
          fixture.tagCooccurrenceByRange[
            timeseriesRangeToCooccurrence(trendWindowDaysToTimeseriesRange(capturedDays))
          ] ?? null,
          fixture.symptomTagCooccurrenceByRange[
            timeseriesRangeToCooccurrence(trendWindowDaysToTimeseriesRange(capturedDays))
          ] ?? null,
          fixture.tagHeatmap,
          fixture.symptomHeatmap,
          exploreEventsWorkContextHeatmap,
          true
        );
        return;
      }

      const response = await fetchInsightEventWindows(
        insight.id,
        timeseriesRangeToCooccurrence(trendWindowDaysToTimeseriesRange(capturedDays))
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

      exploreEventsLoading = false;
      exploreEventsPartnerLoading = true;
      void ensureExploreEventsPartnerData(insight, requestId, insightId, capturedDays);
    } catch {
      if (requestId !== exploreEventsRequestId || exploreEventsInsight?.id !== insightId) {
        return;
      }
      exploreEventsWindows = [];
      exploreEventsPoints = [];
      exploreEventsLagOffset = null;
      exploreEventsPartner = null;
      exploreEventsPartnerCandidates = [];
      exploreEventsPartnerPresence = [];
      exploreEventsPartnerLoading = false;
      exploreEventsPartnerUnavailable = false;
    } finally {
      if (requestId === exploreEventsRequestId && exploreEventsInsight?.id === insightId) {
        exploreEventsLoading = false;
      }
    }
  }

  function applyExploreEventsPartner(
    insight: InsightResponse,
    tagPairs: TagCooccurrenceResponse | null,
    symptomCells: SymptomTagCooccurrenceResponse | null,
    tagHeatmap: TagHeatmapResponse | null,
    symptomHeatmapData: SymptomHeatmapResponse | null,
    workContextHeatmapData: ReturnType<typeof buildWorkContextHeatmap> | null,
    presenceAvailable: boolean
  ): void {
    const carriedPartner = fixedPartnerForInsight(insight);
    if (carriedPartner) {
      exploreEventsPartnerCandidates = [{ ...carriedPartner, score: Number.MAX_SAFE_INTEGER }];
      exploreEventsPartner = presenceAvailable ? carriedPartner : null;
      exploreEventsPartnerPresence = presenceAvailable
        ? presenceDatesForPartner(
            carriedPartner,
            tagHeatmap,
            symptomHeatmapData,
            workContextHeatmapData
          )
        : [];
      return;
    }
    const subject = resolveEsmAlignSubject(insight);
    if (!subject) {
      exploreEventsPartnerCandidates = [];
      exploreEventsPartner = null;
      exploreEventsPartnerPresence = [];
      return;
    }
    const ranked =
      subject.kind === 'tag'
        ? candidatesFromTagCooccurrence(subject, tagPairs?.pairs ?? [])
        : candidatesFromSymptomTagCooccurrence(subject, symptomCells?.cells ?? []);
    exploreEventsPartnerCandidates = clampPartnerCandidates(ranked);
    if (!presenceAvailable) {
      exploreEventsPartner = null;
      exploreEventsPartnerPresence = [];
      return;
    }
    exploreEventsPartner = pickDefaultPartner(exploreEventsPartnerCandidates);
    exploreEventsPartnerPresence = presenceDatesForPartner(
      exploreEventsPartner,
      tagHeatmap,
      symptomHeatmapData,
      workContextHeatmapData
    );
  }

  function fixedPartnerForInsight(insight: InsightResponse): EsmPartner | null {
    if (!carriedPair || !insightMatchesAnalysisPair(insight, carriedPair)) return null;
    const ref: AnalysisSignalRef | null = partnerForInsight(insight, carriedPair);
    if (!ref || !['tag', 'symptom', 'work_context'].includes(ref.kind)) return null;
    return {
      id: ref.id,
      label: ref.label ?? ref.context ?? ref.id,
      kind: ref.kind as EsmPartner['kind'],
    };
  }

  async function ensureExploreEventsPartnerData(
    insight: InsightResponse,
    requestId: number,
    insightId: string,
    days: TrendWindowDays
  ): Promise<void> {
    const subject = resolveEsmAlignSubject(insight);
    const fixedPartner = fixedPartnerForInsight(insight);
    if (!subject && !fixedPartner) {
      exploreEventsPartnerLoading = false;
      return;
    }

    const needsTagPairs = !fixedPartner && subject?.kind === 'tag';
    const needsSymptomCells = !fixedPartner && subject?.kind === 'symptom';
    const apiRange = timeseriesRangeToCooccurrence(trendWindowDaysToTimeseriesRange(days));
    const { start_date, end_date } = trendWindowDateBounds(days);
    const heatmapStart = shiftIsoDate(start_date, -SMALL_MULTIPLES_RADIUS);
    const heatmapEnd = shiftIsoDate(end_date, SMALL_MULTIPLES_RADIUS);

    const tagHeatmapPromise =
      !fixedPartner || fixedPartner.kind === 'tag'
        ? fetchTagHeatmap({ start_date: heatmapStart, end_date: heatmapEnd })
            .then((data) => ({ ok: true as const, data }))
            .catch(() => ({ ok: false as const, data: null }))
        : Promise.resolve({ ok: true as const, data: null });
    const symptomHeatmapPromise =
      fixedPartner?.kind === 'symptom'
        ? fetchSymptomHeatmap({ start_date: heatmapStart, end_date: heatmapEnd })
            .then((data) => ({ ok: true as const, data }))
            .catch(() => ({ ok: false as const, data: null }))
        : Promise.resolve({ ok: true as const, data: visibleSymptomHeatmap ?? symptomHeatmap });
    const workContextEntriesPromise =
      fixedPartner?.kind === 'work_context'
        ? listEntries({ start_date: heatmapStart, end_date: heatmapEnd, limit: 365 })
            .then((data) => ({ ok: true as const, data }))
            .catch(() => ({ ok: false as const, data: null }))
        : Promise.resolve({ ok: true as const, data: null });

    const [
      tagPairsResult,
      symptomCellsResult,
      tagHeatmapResult,
      symptomHeatmapResult,
      workContextEntriesResult,
    ] = await Promise.all([
      needsTagPairs
        ? cooccurrence && cooccurrence.range === apiRange
          ? Promise.resolve({ ok: true as const, data: cooccurrence })
          : fetchTagCooccurrence({ range: apiRange })
              .then((data) => ({ ok: true as const, data }))
              .catch(() => ({ ok: false as const, data: null }))
        : Promise.resolve({ ok: true as const, data: null }),
      needsSymptomCells
        ? symptomCooccurrence && symptomCooccurrence.range === apiRange
          ? Promise.resolve({ ok: true as const, data: symptomCooccurrence })
          : fetchSymptomTagCooccurrence({ range: apiRange })
              .then((data) => ({ ok: true as const, data }))
              .catch(() => ({ ok: false as const, data: null }))
        : Promise.resolve({ ok: true as const, data: null }),
      tagHeatmapPromise,
      symptomHeatmapPromise,
      workContextEntriesPromise,
    ]);

    if (requestId !== exploreEventsRequestId || exploreEventsInsight?.id !== insightId) {
      return;
    }

    const workContextHeatmapData = workContextEntriesResult.data
      ? buildWorkContextHeatmap(workContextEntriesResult.data, {
          start_date: heatmapStart,
          end_date: heatmapEnd,
        })
      : null;
    const presenceAvailable = fixedPartner
      ? fixedPartner.kind === 'tag'
        ? tagHeatmapResult.ok && tagHeatmapResult.data !== null
        : fixedPartner.kind === 'symptom'
          ? symptomHeatmapResult.ok && symptomHeatmapResult.data !== null
          : workContextEntriesResult.ok && workContextHeatmapData !== null
      : tagHeatmapResult.ok && tagHeatmapResult.data !== null;
    const candidatesAvailable = tagPairsResult.ok && symptomCellsResult.ok;
    exploreEventsTagHeatmap = tagHeatmapResult.data;
    exploreEventsSymptomHeatmap = symptomHeatmapResult.data;
    exploreEventsWorkContextHeatmap = workContextHeatmapData;
    exploreEventsPartnerLoading = false;
    applyExploreEventsPartner(
      insight,
      tagPairsResult.data,
      symptomCellsResult.data,
      tagHeatmapResult.data,
      symptomHeatmapResult.data,
      workContextHeatmapData,
      presenceAvailable
    );
    // A failed candidate lookup produces zero candidates, which would otherwise
    // read as "no partner exists". A failed presence fetch only matters once a
    // partner could have been shown.
    exploreEventsPartnerUnavailable =
      (!fixedPartner && !candidatesAvailable) ||
      (!presenceAvailable && exploreEventsPartnerCandidates.length > 0);
  }

  function handleExplorePartnerChange(event: CustomEvent<{ partnerId: string | null }>): void {
    const nextId = event.detail.partnerId;
    const next =
      exploreEventsPartnerCandidates.find((candidate) => candidate.id === nextId) ?? null;
    if (!next) {
      exploreEventsPartner = null;
      exploreEventsPartnerPresence = [];
      return;
    }
    exploreEventsPartner = { id: next.id, label: next.label, kind: next.kind };
    exploreEventsPartnerPresence = presenceDatesForPartner(
      exploreEventsPartner,
      exploreEventsTagHeatmap,
      exploreEventsSymptomHeatmap ?? visibleSymptomHeatmap ?? symptomHeatmap,
      exploreEventsWorkContextHeatmap
    );
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
  <ScreenHeader title={$_('insights.page.title')} subtitle={$_('insights.page.subtitle')} sticky>
    <svelte:fragment slot="controls">
      {#if $auth.status === 'authenticated'}
        <InsightsAnalysisToolbar
          analysisRange={$analysisRange}
          analysisRangeOptions={analysisRangeControlOptions}
          on:rangeChange={(event) => {
            const nextDays = coerceTrendWindowDays(event.detail.value);
            setAnalysisRange(nextDays);
            void updateUserPreferences({ trend_window_days: nextDays }).catch(() => {
              // Optimistic local window; server sync can retry on next visit.
            });
          }}
        />
      {/if}
    </svelte:fragment>
  </ScreenHeader>
  <p class="insights-page__history-link">
    <a href="/insights/history">{$_('insights.page.history_link')}</a>
    <span aria-hidden="true"> · </span>
    <a href="/insights/report" data-testid="insights-report-link"
      >{$_('insights.page.report_link')}</a
    >
  </p>

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('insights.page.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">
        {$_('auth.login.submit')}
      </Button>
    </Panel>
  {:else}
    <!-- Configurable sections in stored order (#821/#823). Each still respects
         its existing phase/data gate; user visibility is an additional AND-gate.
         The readiness stage header (#823) is now a regular section here; the
         milestone-only strip still lives inside MobileInsightLead, so
         showStageMilestone suppresses the duplicate on mobile-with-primary. -->
    {#if showBelastungOverlay && belastungInsight}
      <BelastungOverlay
        insight={belastungInsight}
        analyticsEnabled={userPreferences?.analytics_enabled !== false}
      />
    {/if}

    {#each enabledInsightSectionKeys as sectionKey (sectionKey)}
      {#if sectionKey === 'stage_header'}
        {#if insightMaturity}
          <InsightStageHeader
            maturity={insightMaturity}
            showMilestone={showStageMilestone}
            on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
          />
        {/if}
      {:else if sectionKey === 'correlation_matrix'}
        {#if showMatrix}
          <section class="insights-page__matrix" data-testid="insights-matrix-section">
            <InsightMatrix {insights} />
          </section>
        {/if}
      {:else if sectionKey === 'insight_feed'}
        <div class="insights-page__feed" data-testid="insight-section-insight_feed">
          {#if compactInsights && !feedLoading && !error && primaryMobileInsight}
            <MobileInsightLead
              insight={primaryMobileInsight}
              detailQuery={carriedPairQuery}
              maturity={insightMaturity}
              entryCount={visibleEntryCount}
              {inactiveTagIds}
              showMilestone={showLeadMilestone}
              {enableExploreEvents}
              on:dismiss={(event) => void handleDismissInsight(event.detail.id)}
              on:exploreEvents={(event) => void openExploreEvents(event.detail.id)}
              on:dismissMilestone={(event) => void dismissMaturityMilestone(event.detail.key)}
              on:openDisclaimer={() => (disclaimerOpen = true)}
            />
          {/if}

          {#if !compactInsights && primaryMobileInsight}
            <AnalysisCrossLink insight={primaryMobileInsight} direction="to-trends" />
          {/if}

          {#if carriedSignalsUnmatched}
            <!--
              The pair came from Compare, but no generated insight covers it yet.
              Saying so beats dropping the user into an unfiltered hub (#967).
            -->
            <InlineAlert
              variant="info"
              message={$_('insights.carried_signals_unmatched')}
              testId="insights-carried-signals-unmatched"
            />
          {:else if carriedPairFocused}
            <InlineAlert
              variant="info"
              message={$_('insights.carried_pair_focused')}
              testId="insights-carried-pair-focused"
            />
          {/if}

          {#if showInsightFeed}
            {#if compactInsights && primaryMobileInsight}
              <section class="insights-page__more" data-testid="mobile-insights-more">
                {#if feedInsights.length > 0}
                  <h2>{$_('insights.mobile.more_heading')}</h2>
                {/if}
                <InsightFeed
                  insights={feedInsights}
                  detailQuery={carriedPairQuery}
                  stalenessInsights={insights}
                  {lastSuccessfulInsightRunAt}
                  analyticsEnabled={userPreferences?.analytics_enabled !== false}
                  hideContent={feedInsights.length === 0}
                  totalInsightCount={insights.length}
                  maturity={insightMaturity}
                  entryCount={visibleEntryCount}
                  {analysisRangeDays}
                  {inactiveTagIds}
                  dismissedCount={dismissedItems.length}
                  {enableExploreEvents}
                  {regenerateBusy}
                  {regenerateMessage}
                  {regenerateError}
                  showContext={false}
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
                detailQuery={carriedPairQuery}
                stalenessInsights={insights}
                {lastSuccessfulInsightRunAt}
                analyticsEnabled={userPreferences?.analytics_enabled !== false}
                totalInsightCount={insights.length}
                maturity={insightMaturity}
                loading={feedLoading}
                {error}
                entryCount={visibleEntryCount}
                {analysisRangeDays}
                {inactiveTagIds}
                dismissedCount={dismissedItems.length}
                {enableExploreEvents}
                {regenerateBusy}
                {regenerateMessage}
                {regenerateError}
                showMaturityBadge={!pageMaturityChrome}
                on:retry={loadInsights}
                on:regenerate={() => void handleRegenerateInsights()}
                on:dismiss={(event) => void handleDismissInsight(event.detail.id)}
                on:exploreEvents={(event) => void openExploreEvents(event.detail.id)}
                on:selectDate={(event) => void openSymptomHistory(event.detail.date)}
              />
            {/if}
          {/if}
        </div>
      {:else if sectionKey === 'lag_heatmap'}
        {#if showLagHeatmap}
          <section class="insights-page__lag-heatmap" data-testid="insights-lag-heatmap-section">
            <LagCorrelationHeatmap {insights} />
          </section>
        {/if}
      {:else if sectionKey === 'dismissed'}
        <DismissedInsightsSection
          items={dismissedItems}
          maturity={insightMaturity}
          {inactiveTagIds}
          on:undismiss={(event) =>
            void handleUndismissInsight(event.detail.id, event.detail.dismissalId)}
        />
      {:else if sectionKey === 'symptom_analytics'}
        {#if showAdvancedAnalytics && showSymptomAnalytics}
          <div
            class="insights-page__analytics-block"
            data-testid="insight-section-symptom_analytics"
          >
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
          </div>
        {/if}
      {:else if sectionKey === 'tag_groups'}
        {#if showAdvancedAnalytics}
          <div class="insights-page__analytics-block" data-testid="insight-section-tag_groups">
            <TagGroupsSection data={tagClusters} loading={tagClustersLoading} />
          </div>
        {/if}
      {:else if sectionKey === 'tag_cooccurrence'}
        {#if showAdvancedAnalytics && showTagCooccurrencePanel}
          <div
            class="insights-page__analytics-block"
            data-testid="insight-section-tag_cooccurrence"
          >
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
          </div>
        {/if}
      {/if}
    {/each}

    {#if showToolsRow}
      <nav
        class="insights-page__tools"
        data-testid="insights-tools-row"
        aria-label={$_('insights.page.tools_aria')}
      >
        <p class="insights-page__tools-label">{$_('insights.page.tools_heading')}</p>
        <div class="insights-page__tools-links">
          {#if hiddenToolKeys.includes('correlation_matrix')}
            <a href="/insights/report">{$_('insights.page.report_link')}</a>
          {/if}
          {#if !dismissedSectionEnabled && dismissedItems.length > 0}
            <button
              type="button"
              class="insights-page__tools-button"
              data-testid="insights-dismissed-link"
              on:click={() => (showDismissedPanel = !showDismissedPanel)}
            >
              {$_('insights.page.dismissed_link', { values: { count: dismissedItems.length } })}
            </button>
          {/if}
          {#if hiddenToolKeys.some((key) => key !== 'correlation_matrix')}
            <a href="/settings/insights" data-testid="insights-tools-settings-link">
              {$_('insights.page.tools_settings_link')}
            </a>
          {/if}
        </div>
      </nav>
      {#if showDismissedPanel && !dismissedSectionEnabled}
        <DismissedInsightsSection
          items={dismissedItems}
          maturity={insightMaturity}
          {inactiveTagIds}
          on:undismiss={(event) =>
            void handleUndismissInsight(event.detail.id, event.detail.dismissalId)}
        />
      {/if}
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
      partner={exploreEventsPartner}
      partnerPresenceDates={exploreEventsPartnerPresence}
      partnerCandidates={exploreEventsPartnerCandidates}
      partnerLoading={exploreEventsPartnerLoading}
      partnerUnavailable={exploreEventsPartnerUnavailable}
      on:partnerChange={handleExplorePartnerChange}
      on:close={() => {
        exploreEventsOpen = false;
        exploreEventsInsight = null;
        exploreEventsPartner = null;
        exploreEventsPartnerCandidates = [];
        exploreEventsPartnerPresence = [];
        exploreEventsPartnerLoading = false;
        exploreEventsPartnerUnavailable = false;
        exploreEventsTagHeatmap = null;
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

  .insights-page__tools {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-top: var(--space-2);
    padding: 0.75rem 0;
    border-top: 1px solid var(--color-border);
  }

  .insights-page__tools-label {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .insights-page__tools-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 0.85rem;
    font-size: var(--text-sm);
  }

  .insights-page__tools-links a,
  .insights-page__tools-button {
    color: var(--color-primary);
    background: none;
    border: none;
    padding: 0;
    font: inherit;
    cursor: pointer;
    text-align: left;
  }

  .insights-page__matrix {
    min-width: 0;
    max-width: 100%;
    /* Extra clearance so the last matrix rows clear the fixed bottom nav (#628). */
    padding-bottom: var(--space-2);
    margin-bottom: var(--space-2);
  }

  /* #821: analytics blocks are individually orderable now (no shared panel).
     Keep each block from forcing page-level horizontal scroll; wide charts
     scroll inside themselves. */
  .insights-page__feed,
  .insights-page__analytics-block {
    min-width: 0;
    max-width: 100%;
  }

  .insights-page__feed {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap-tight, var(--space-3));
  }

  .insights-page__analytics-block {
    overflow-x: hidden;
  }

  .insights-page__analytics-block > :global(*) {
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
