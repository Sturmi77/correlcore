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
  import { analysisRange } from '$lib/stores/analysisRange';
  import { trendWindowPreference } from '$lib/stores/trendWindowPreference';
  import TrendWindowSaveStatus from '$lib/components/analysis/TrendWindowSaveStatus.svelte';
  import { localIsoDate } from '$lib/utils/isoDate';
  import {
    coerceTrendWindowDays,
    trendWindowDaysToCooccurrence,
    type TrendWindowDays,
  } from '$lib/utils/trendWindowDays';
  import { dayEntryDatesFromIsoEntries } from '$lib/utils/insightQuality';
  import { shouldShowMaturityMilestone } from '$lib/utils/insightMaturityMilestones';
  import { rankInsights } from '$lib/utils/insightRanking';
  import {
    canShowAdvancedAnalytics,
    canShowMatrixTab,
    canShowTagCooccurrence,
  } from '$lib/utils/insightAnalyticsGate';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
  import AnalysisCrossLink from '$lib/components/analysis/AnalysisCrossLink.svelte';
  import { shiftIsoDate } from '$lib/utils/isoDate';
  import { RequestGeneration } from '$lib/utils/requestGeneration';
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
    isSmallMultiplesUnlocked,
    SMALL_MULTIPLES_RADIUS,
  } from '$lib/components/trends/smallMultiplesGate';

  let insights: InsightResponse[] = [];
  let dismissedItems: DismissedInsightItem[] = [];
  let showDismissedPanel = false;
  let loading = false;
  let insightsLoaded = false;
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
  let cooccurrenceError = false;
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
  let symptomCooccurrenceError = false;
  let cooccurrenceRequested = false;
  let cooccurrenceRequestId = 0;
  let symptomCooccurrenceRequested = false;
  let symptomCooccurrenceRequestId = 0;
  let symptomWindowRequestId = 0;
  let symptomWindowLoading = false;
  let exploreEventsOpen = false;
  let exploreEventsDataDays: TrendWindowDays | null = null;
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
  // #918: the sheet opens before partner data arrives — keep "still loading"
  // and "presence data failed" apart from "no partner exists".
  let exploreEventsPartnerLoading = false;
  let exploreEventsPartnerUnavailable = false;
  const insightsRequest = new RequestGeneration();
  const symptomWindowRequest = new RequestGeneration();
  const cooccurrenceRequest = new RequestGeneration();
  const symptomCooccurrenceRequest = new RequestGeneration();
  const exploreEventsRequest = new RequestGeneration();
  let lastInsightsActor: string | null = null;
  $: insightsActor = $auth.status === 'authenticated' ? $auth.user.id : null;
  $: if (insightsActor !== lastInsightsActor) {
    const previousActor = lastInsightsActor;
    lastInsightsActor = insightsActor;
    trendWindowPreference.bind(insightsActor);
    insightsRequest.cancel();
    symptomWindowRequest.cancel();
    cooccurrenceRequest.cancel();
    symptomCooccurrenceRequest.cancel();
    exploreEventsRequest.cancel();
    if (previousActor !== null) {
      insights = [];
      dismissedItems = [];
      cooccurrence = null;
      symptomCooccurrence = null;
      clearSymptomWindowData();
      insightsLoaded = false;
      loading = false;
      cooccurrenceLoading = false;
      symptomCooccurrenceLoading = false;
      cooccurrenceRequested = false;
      symptomCooccurrenceRequested = false;
      lastWindowDaysForCooccurrence = null;
    }
  }

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
  $: cooccurrenceRange = trendWindowDaysToCooccurrence(windowDays);
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
    return trendWindowDaysToCooccurrence(days);
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
    const actor = get(auth);
    if (actor.status !== 'authenticated') return;
    const requestedDays = windowDays;
    const request = symptomWindowRequest.begin(`${actor.user.id}:${requestedDays}`);
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
      if (
        !request.isCurrent() ||
        requestId !== symptomWindowRequestId ||
        requestedDays !== windowDays
      )
        return;
      applySymptomWindowData(entries, heatmap, requestedDays);
    } catch {
      // Keep the current range empty rather than mixing entries and heatmap from different windows.
    } finally {
      if (request.isCurrent() && requestId === symptomWindowRequestId) {
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
  $: if (exploreEventsOpen && exploreEventsInsight && exploreEventsDataDays !== windowDays) {
    void openExploreEvents(exploreEventsInsight.id);
  }

  function devFixtureKey(): string {
    return `${$devPhase.presetId}:${$devPhase.entryCount}:${$devPhase.onboardingCompleted}`;
  }

  async function loadCooccurrence(): Promise<void> {
    const actor = get(auth);
    if (actor.status !== 'authenticated') return;
    cooccurrenceRequested = true;
    const requestedDays = windowDays;
    const request = cooccurrenceRequest.begin(`${actor.user.id}:${requestedDays}`);
    const requestedRange = cooccurrenceRange;
    const requestId = ++cooccurrenceRequestId;
    cooccurrenceLoading = true;
    cooccurrenceError = false;
    try {
      const nextCooccurrence = get(devForceVisualizations)
        ? getDevPhaseFixture(get(devPhase)).tagCooccurrenceByRange[requestedRange]
        : await fetchTagCooccurrence({
            range: requestedRange,
            days: requestedDays,
            end_date: trendWindowDateBounds(requestedDays).end_date,
            min_count: 2,
            signal: request.signal,
          });
      if (
        request.isCurrent() &&
        requestId === cooccurrenceRequestId &&
        requestedRange === cooccurrenceRange
      ) {
        cooccurrence = nextCooccurrence;
        cooccurrenceError = false;
      }
    } catch {
      if (
        request.isCurrent() &&
        requestId === cooccurrenceRequestId &&
        requestedRange === cooccurrenceRange
      ) {
        cooccurrence = null;
        cooccurrenceError = true;
      }
    } finally {
      if (request.isCurrent() && requestId === cooccurrenceRequestId) {
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
    const actor = get(auth);
    if (actor.status !== 'authenticated') return;
    symptomCooccurrenceRequested = true;
    const requestedDays = windowDays;
    const request = symptomCooccurrenceRequest.begin(`${actor.user.id}:${requestedDays}`);
    const requestedRange = cooccurrenceRange;
    const requestId = ++symptomCooccurrenceRequestId;
    symptomCooccurrenceLoading = true;
    symptomCooccurrenceError = false;
    try {
      const nextSymptomCooccurrence = get(devForceVisualizations)
        ? getDevPhaseFixture(get(devPhase)).symptomTagCooccurrenceByRange[requestedRange]
        : await fetchSymptomTagCooccurrence({
            range: requestedRange,
            days: requestedDays,
            end_date: trendWindowDateBounds(requestedDays).end_date,
            min_count: 3,
            signal: request.signal,
          });
      if (
        request.isCurrent() &&
        requestId === symptomCooccurrenceRequestId &&
        requestedRange === cooccurrenceRange
      ) {
        symptomCooccurrence = nextSymptomCooccurrence;
        symptomCooccurrenceError = false;
      }
    } catch {
      if (
        request.isCurrent() &&
        requestId === symptomCooccurrenceRequestId &&
        requestedRange === cooccurrenceRange
      ) {
        symptomCooccurrence = null;
        symptomCooccurrenceError = true;
      }
    } finally {
      if (request.isCurrent() && requestId === symptomCooccurrenceRequestId) {
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
    const actor = get(auth);
    if (actor.status !== 'authenticated') return;
    const request = insightsRequest.begin(`${actor.user.id}:${windowDays}`);
    const preferenceRevision = trendWindowPreference.revision();
    loading = true;
    error = null;
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
      if (!request.isCurrent()) return;

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
      if (preferencesResult.status === 'fulfilled') {
        trendWindowPreference.hydrate(
          actor.user.id,
          preferencesResult.value.trend_window_days,
          preferenceRevision
        );
      }

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
      if (!request.isCurrent()) return;
      const dismissedInsightIds = new Set(dismissedItems.map((item) => item.insight.id));
      if (dismissedInsightIds.size > 0) {
        insights = insights.filter((insight) => !dismissedInsightIds.has(insight.id));
      }
    } catch (err) {
      if (!request.isCurrent()) return;
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
      if (request.isCurrent()) {
        loading = false;
        insightsLoaded = true;
      }
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
    // Read straight from the URL rather than the page store: this runs in unit
    // tests too, where no SvelteKit runtime provides one.
    if (browser) {
      carriedSignalIds = (new URLSearchParams(window.location.search).get('signals') ?? '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean);
    }
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
      insightsRequest.cancel();
      symptomWindowRequest.cancel();
      cooccurrenceRequest.cancel();
      symptomCooccurrenceRequest.cancel();
      exploreEventsRequest.cancel();
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
