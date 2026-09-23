<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { hasNote } from '$lib/utils/noteSummary';
  import {
    fetchHealthContext,
    fetchSymptomHeatmap,
    fetchTagHeatmap,
    fetchTimeseries,
    type HealthContextResponse,
    type SymptomHeatmapResponse,
    type TagHeatmapResponse,
    type TimeseriesRange,
    type TimeseriesResponse,
  } from '$lib/api/stats';
  import type { InsightMaturity } from '$lib/api/insights';
  import { listHabits, type HabitStatsResponse, type HabitWindow } from '$lib/api/habits';
  import { fetchUserPreferences } from '$lib/api/preferences';
  import { listSymptomsForEntry, listVisibleSymptoms } from '$lib/api/symptoms';
  import { listTagsForEntry, listVisibleTags, type TagResponse } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';
  import type { TagCategory } from '$lib/api/tags';
  import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { analysisRange } from '$lib/stores/analysisRange';
  import { trendWindowPreference } from '$lib/stores/trendWindowPreference';
  import TrendWindowSaveStatus from '$lib/components/analysis/TrendWindowSaveStatus.svelte';
  import { insightStore, loadInsights, rankedInsights } from '$lib/stores/insights';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';
  import { scheduleSync } from '$lib/offline/syncOrchestrator';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/isoDate';
  import { RequestGeneration } from '$lib/utils/requestGeneration';
  import { smoothTimeseriesPoints } from '$lib/utils/charts';
  import {
    rangeToDays,
    readSmoothingPreference,
    smoothingWindowDays,
    TREND_SMOOTHING_STORAGE_KEY,
  } from '$lib/utils/trendsRange';
  import {
    coerceTrendWindowDays,
    trendWindowDaysToTimeseriesRange,
    type TrendWindowDays,
  } from '$lib/utils/trendWindowDays';
  import {
    buildWorkContextHeatmap,
    type WorkContextHeatmapResponse,
  } from '$lib/utils/workContextHeatmap';
  import TrendsAnalysisToolbar from '$lib/components/trends/TrendsAnalysisToolbar.svelte';
  import TrendsComparePanel from '$lib/components/trends/TrendsComparePanel.svelte';
  import TrendsCompareFilters from '$lib/components/trends/TrendsCompareFilters.svelte';
  import TrendsCompareQuickFilters from '$lib/components/trends/TrendsCompareQuickFilters.svelte';
  import TrendsCompareSettingsSheet from '$lib/components/trends/TrendsCompareSettingsSheet.svelte';
  import TrendsHealthContext from '$lib/components/trends/TrendsHealthContext.svelte';
  import HabitsPanel from '$lib/components/trends/HabitsPanel.svelte';
  import EntryHistorySheet, {
    type EntryHistoryDetail,
  } from '$lib/components/trends/EntryHistorySheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import type { SegmentedControlOption } from '$lib/components/common/SegmentedControl.svelte';
  import type { TabBarOption } from '$lib/components/common/TabBar.svelte';
  import AnalysisCrossLink from '$lib/components/analysis/AnalysisCrossLink.svelte';
  import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
  import { changepointInsightsToMarkers } from '$lib/utils/changepointMarkers';
  import type { EsmPartner } from '$lib/utils/esmPartner';
  import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';
  import {
    readCompareMode,
    readCompareSortMode,
    readCompareZoomStage,
    readCompareCoincidenceHighlight,
    readCompareLag1Highlight,
    readCompareOverlayHintDismissed,
    writeCompareMode,
    writeCompareSortMode,
    writeCompareZoomStage,
    writeCompareCoincidenceHighlight,
    writeCompareLag1Highlight,
    writeCompareOverlayHintDismissed,
    type CompareMode,
    type CompareSortMode,
  } from '$lib/utils/comparePanelSettings';
  import { clampZoomStageForWindow, type CompareZoomStageIndex } from '$lib/utils/compareAxisZoom';
  import EventAlignedSmallMultiplesSheet from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import type { EventWindow } from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import { isSmallMultiplesUnlocked } from '$lib/components/trends/smallMultiplesGate';
  import {
    EMPTY_COMPARE_OVERLAY_AVAILABILITY,
    type CompareOverlayAvailability,
  } from '$lib/utils/compareOverlayAvailability';
  import {
    applySleepZeitversatz,
    readSleepZeitversatzPreference,
    writeSleepZeitversatzPreference,
  } from '$lib/utils/sleepZeitversatz';

  type TrendTab = 'compare' | 'habits';

  const rangeOptions: { id: string; label: string }[] = [
    { id: '14', label: 'trends.range.d14' },
    { id: '28', label: 'trends.range.d28' },
    { id: '90', label: 'trends.range.d90' },
  ];

  const tabs: { id: TrendTab; label: string }[] = [
    { id: 'compare', label: 'trends.tabs.compare' },
    { id: 'habits', label: 'trends.tabs.habits' },
  ];

  let activeTab: TrendTab = 'compare';
  let selectedCategory: TagCategory | 'all' = 'all';
  let timeseries: TimeseriesResponse | null = null;
  /** Analysis window the current `timeseries` was loaded for. */
  let loadedWindowDays: TrendWindowDays | null = null;
  const trendsRequest = new RequestGeneration();
  let lastAuthUserId: string | null = null;
  $: authUserId = $auth.status === 'authenticated' ? $auth.user.id : null;
  $: if (authUserId !== lastAuthUserId) {
    const previousActor = lastAuthUserId;
    lastAuthUserId = authUserId;
    trendWindowPreference.bind(authUserId);
    trendsRequest.cancel();
    if (previousActor !== null) {
      timeseries = null;
      heatmap = null;
      symptomHeatmap = null;
      trendEntries = [];
      loadedWindowDays = null;
      loading = false;
      trendsLoaded = false;
    }
  }
  let preferenceLoadedActor: string | null = null;
  $: if (authUserId && preferenceLoadedActor !== authUserId) {
    preferenceLoadedActor = authUserId;
    const revision = trendWindowPreference.revision();
    void fetchUserPreferences()
      .then((prefs) =>
        trendWindowPreference.hydrate(authUserId!, prefs.trend_window_days, revision)
      )
      .catch(() => {
        // The current local choice remains available while offline.
      });
  }
  $: if (!authUserId) preferenceLoadedActor = null;
  let heatmap: TagHeatmapResponse | null = null;
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let healthContext: HealthContextResponse | null = null;
  // Maturity for the reused InsightStageHeader (spec G1). Dev-force uses the
  // fixture's maturity; otherwise the canonical insight-store maturity.
  let devMaturity: InsightMaturity | null = null;
  let habitStats: HabitStatsResponse[] = [];
  let habitTags: TagResponse[] = [];
  let allTags: TagResponse[] = [];
  let cycleEntries: EntryResponse[] = [];
  let trendEntries: EntryResponse[] = [];
  let workContextHeatmap: WorkContextHeatmapResponse | null = null;
  let metrics: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
    sleep_quality_avg: true,
    sleep_minutes_avg: false,
  };
  let loading = false;
  let trendsLoaded = false;
  let error = '';
  let historyOpen = false;
  let historyDate = '';
  let historyLoading = false;
  let historyError = '';
  let historyDetails: EntryHistoryDetail[] = [];
  // Default on: softer trend is the primary read for 30D+ (and week with a
  // shorter window). Explicit localStorage Raw choice still wins on mount.
  let smoothing = true;
  let showTagRows = true;
  let showSymptomRows = false;
  let showWorkContextRows = true;
  let compactTrends = false;
  let compareSettingsOpen = false;
  let compareClusterRefreshToken = 0;
  let compareClustersAvailable = false;
  let compareMode: CompareMode = 'lines';
  let compareSortMode: CompareSortMode = 'frequency';
  // #919: the overlays live in the panel but are also operable from the mobile
  // settings sheet, so the page holds the shared state.
  let compareCoincidenceHighlight = false;
  let compareLag1Highlight = false;
  let compareOverlayHintDismissed = false;
  let compareOverlayAvailability: CompareOverlayAvailability = EMPTY_COMPARE_OVERLAY_AVAILABILITY;
  let sleepZeitversatz = false;
  let compareFocusedClusterId: number | null = null;
  let compareZoomStage: CompareZoomStageIndex = readCompareZoomStage();
  let compareTagClusterLabels: { cluster_id: number; label: string }[] = [];
  let compareEsmOpen = false;
  let compareEsmWindows: EventWindow[] = [];
  let compareEsmPartner: EsmPartner | null = null;
  let compareEsmPartnerDates: readonly string[] = [];
  let mobileMedia: MediaQueryList | null = null;
  let activeDevFixtureKey = '';

  const COMPARE_LAYERS_STORAGE_KEY = 'cc_trend_compare_layers';

  $: windowDays = $analysisRange;
  $: panelMaturity = $devForceVisualizations ? devMaturity : $insightStore.insightMaturity;
  $: noteEntryDates = trendEntries
    .filter((entry) => hasNote(entry))
    .map((entry) => entry.entry_date);

  function dateWindow(
    activeRange: TimeseriesRange,
    days?: number
  ): { start_date: string; end_date: string } {
    const windowDays = days ?? rangeToDays(activeRange);
    const end_date = localIsoDate(new Date());
    return { start_date: shiftIsoDate(end_date, -(windowDays - 1)), end_date };
  }

  function devFixtureKey(): string {
    return `${$devPhase.presetId}:${$devPhase.entryCount}:${$devPhase.onboardingCompleted}`;
  }

  async function loadTrends(rangeOverride?: TrendWindowDays): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    const requestUserId = $auth.user.id;
    const activeWindowDays: TrendWindowDays = rangeOverride ?? windowDays;
    const request = trendsRequest.begin(
      `${requestUserId}:${activeWindowDays}:${activeTab}:${selectedCategory}`
    );
    // Record the window this load is for *before* awaiting. The reload guard
    // below compares against this, never against a field of the response: a
    // response that omits it (older backend, cached service-worker entry, a
    // test fixture) would otherwise never satisfy the guard and the reactive
    // statement would re-enter loadTrends forever.
    //
    // Stamping before the await also means a *failed* load marks the window as
    // attempted, so the guard does not retry it on its own. That is deliberate:
    // the alternative — clearing it on error — turns a persistent failure into a
    // retry storm, the same shape of bug in slower motion. The error is shown,
    // and a range change or page refresh retries.
    loadedWindowDays = activeWindowDays;
    const activeRange = trendWindowDaysToTimeseriesRange(activeWindowDays);
    const habitWindow = activeWindowDays as HabitWindow;
    loading = true;
    error = '';
    // Drop previous context rows and entry markers immediately so an empty
    // target range cannot keep showing Kontextzeilen from the prior window.
    heatmap = null;
    symptomHeatmap = null;
    workContextHeatmap = null;
    if (timeseries) {
      timeseries = { ...timeseries, points: [] };
    }
    try {
      if ($devForceVisualizations) {
        const fixture = getDevPhaseFixture($devPhase);
        activeDevFixtureKey = devFixtureKey();
        timeseries = { ...fixture.timeseries, range: activeRange };
        heatmap = fixture.tagHeatmap;
        symptomHeatmap = fixture.symptomHeatmap;
        healthContext = fixture.healthContext;
        devMaturity = fixture.maturity;
        habitStats = fixture.habitStats.map((habit) => ({ ...habit, window: habitWindow }));
        habitTags = fixture.habitTags;
        allTags = fixture.habitTags;
        cycleEntries = fixture.entries.filter((entry) => entry.cycle_day !== null);
        trendEntries = fixture.entries;
        workContextHeatmap = buildWorkContextHeatmap(
          fixture.entries,
          dateWindow(activeRange, activeWindowDays)
        );
        return;
      }

      const { start_date, end_date } = dateWindow(activeRange, activeWindowDays);
      // Soft-fail the symptom heatmap: a single 401/5xx must not blank the
      // whole Compare tab (Promise.all would reject on the first failure).
      const symptomPromise =
        activeTab === 'compare'
          ? fetchSymptomHeatmap({ start_date, end_date })
          : Promise.resolve(symptomHeatmap);
      const [
        timeseriesResult,
        heatmapResult,
        symptomResult,
        healthContextResult,
        entriesResult,
        habitResult,
        tagsResult,
      ] = await Promise.allSettled([
        // Exact window: the enum alone would fetch 7 days for a 14-day
        // selection and 30 for a 28-day one (#867).
        fetchTimeseries(activeRange, activeWindowDays, {
          end_date,
          signal: request.signal,
        }),
        fetchTagHeatmap({
          start_date,
          end_date,
          ...(activeTab === 'compare' && selectedCategory !== 'all'
            ? { category: selectedCategory }
            : {}),
        }),
        symptomPromise,
        fetchHealthContext(),
        listEntries({ start_date, end_date, limit: 365 }),
        activeTab === 'habits' ? listHabits(habitWindow) : Promise.resolve({ habits: habitStats }),
        activeTab === 'habits' ? listVisibleTags() : Promise.resolve(habitTags),
      ]);
      if (
        !request.isCurrent() ||
        $auth.status !== 'authenticated' ||
        $auth.user.id !== requestUserId ||
        activeWindowDays !== $analysisRange
      )
        return;

      // Health context is optional context — a failure must not blank the tab.
      const coreFailed = [timeseriesResult, heatmapResult, entriesResult].find(
        (result) => result.status === 'rejected'
      );
      if (coreFailed && coreFailed.status === 'rejected') {
        const reason = coreFailed.reason;
        throw reason instanceof Error ? reason : new Error($_('error.generic'));
      }

      if (timeseriesResult.status === 'fulfilled') timeseries = timeseriesResult.value;
      if (heatmapResult.status === 'fulfilled') heatmap = heatmapResult.value;
      // Symptom rows are optional context — keep Compare usable if this call fails.
      symptomHeatmap = symptomResult.status === 'fulfilled' ? symptomResult.value : null;
      healthContext = healthContextResult.status === 'fulfilled' ? healthContextResult.value : null;
      if (entriesResult.status === 'fulfilled') {
        const nextEntries = entriesResult.value;
        cycleEntries = nextEntries.filter((entry) => entry.cycle_day !== null);
        trendEntries = nextEntries;
        workContextHeatmap = buildWorkContextHeatmap(nextEntries, { start_date, end_date });
      }
      if (habitResult.status === 'fulfilled') habitStats = habitResult.value.habits;
      else if (activeTab === 'habits') {
        const habitErr = habitResult.reason;
        error = habitErr instanceof Error ? habitErr.message : $_('error.generic');
      }
      if (tagsResult.status === 'fulfilled') {
        allTags = tagsResult.value;
        habitTags = tagsResult.value.filter((tag) => tag.habit_type !== 'none');
      }
    } catch (err) {
      if (request.isCurrent()) error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      if (request.isCurrent()) {
        loading = false;
        trendsLoaded = true;
      }
    }
  }

  function toggleMetric(metric: MetricKey): void {
    metrics = { ...metrics, [metric]: !metrics[metric] };
  }

  function setSmoothing(value: boolean): void {
    smoothing = value;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(TREND_SMOOTHING_STORAGE_KEY, value ? 'true' : 'false');
    }
  }

  function setCompareLayers(next: {
    showTags: boolean;
    showSymptoms: boolean;
    showWorkContexts: boolean;
  }): void {
    showTagRows = next.showTags;
    showSymptomRows = next.showSymptoms;
    showWorkContextRows = next.showWorkContexts;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(COMPARE_LAYERS_STORAGE_KEY, JSON.stringify(next));
    }
  }

  function restoreCompareLayers(): void {
    if (typeof localStorage === 'undefined') return;
    try {
      const raw = localStorage.getItem(COMPARE_LAYERS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<{
        showTags: boolean;
        showSymptoms: boolean;
        showWorkContexts: boolean;
      }>;
      if (typeof parsed.showTags === 'boolean') showTagRows = parsed.showTags;
      if (typeof parsed.showSymptoms === 'boolean') showSymptomRows = parsed.showSymptoms;
      if (typeof parsed.showWorkContexts === 'boolean') {
        showWorkContextRows = parsed.showWorkContexts;
      }
    } catch {
      localStorage.removeItem(COMPARE_LAYERS_STORAGE_KEY);
    }
  }

  async function openHistory(date: string): Promise<void> {
    historyOpen = true;
    historyDate = date;
    historyLoading = true;
    historyError = '';
    historyDetails = [];
    try {
      if ($devForceVisualizations) {
        const fixture = getDevPhaseFixture($devPhase);
        historyDetails = fixture.entries
          .filter((entry) => entry.entry_date === date)
          .map((entry) => ({
            entry,
            tags: fixture.tagsByEntryId[entry.id] ?? [],
            symptoms:
              fixture.symptomsByEntryId[entry.id] ??
              fixture.symptomHeatmap.symptoms.map((symptom) => ({
                name: symptom.name,
                intensity: symptom.days.find((day) => day.date === date)?.max_intensity ?? 1,
              })),
          }));
        return;
      }

      const entries = await listEntries({ start_date: date, end_date: date, limit: 365 });
      const visibleSymptoms = await listVisibleSymptoms();
      const symptomNames = new Map(visibleSymptoms.map((symptom) => [symptom.id, symptom.name]));
      historyDetails = await Promise.all(
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
      historyError = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      historyLoading = false;
    }
  }

  // Hydrate may finish after onMount — mirror Insights and load once auth is ready.
  $: if ($auth.status === 'authenticated' && !trendsLoaded && !loading) {
    void loadTrends();
  }
  $: if (
    $auth.status === 'authenticated' &&
    // The window this data was loaded for, not a field of the response. The
    // coarse enum could not tell 14 from 28 correctly, and reading `days` off
    // the response makes the guard unsatisfiable whenever the field is absent.
    loadedWindowDays !== null &&
    loadedWindowDays !== $analysisRange &&
    !loading
  ) {
    void loadTrends($analysisRange);
  }
  $: habitWindow = $analysisRange as HabitWindow;
  $: if (
    $auth.status === 'authenticated' &&
    $devForceVisualizations &&
    timeseries &&
    !loading &&
    activeDevFixtureKey !== devFixtureKey()
  ) {
    void loadTrends();
  }
  $: rangeControlOptions = rangeOptions.map((option): SegmentedControlOption => ({
    id: option.id,
    label: $_(option.label),
    testId: `trends-range-${option.id}`,
  }));
  $: trendTabOptions = tabs.map((tab): TabBarOption => ({
    id: tab.id,
    label: $_(tab.label),
    testId: `trends-tab-${tab.id}`,
  }));
  // Smoothing is available for every range; week uses a 3-day window so the
  // daily shape stays readable (see smoothingWindowDays).
  $: smoothingAvailable = true;
  $: displayRange = trendWindowDaysToTimeseriesRange(windowDays);
  $: displayTimeseries = (() => {
    const base =
      timeseries && smoothing && smoothingAvailable
        ? {
            ...timeseries,
            points: smoothTimeseriesPoints(timeseries.points, smoothingWindowDays(displayRange)),
          }
        : timeseries;
    if (!base) return base;
    return {
      ...base,
      points: applySleepZeitversatz(base.points, sleepZeitversatz),
    };
  })();
  $: topInsight = $insightStore.latest;
  // The dismissed-filtered view, not the raw list: a changepoint removed from the
  // feed kept drawing its Compare marker, because dismissals live in a separate
  // field of the store and only the derived value applies them (#964).
  $: changepointMarkers = changepointInsightsToMarkers($rankedInsights, $_, {
    axisStart: displayTimeseries?.points?.[0]?.period_start,
    axisEnd: displayTimeseries?.points?.[displayTimeseries.points.length - 1]?.period_start,
  }) satisfies EventMarker[];
  $: compareEsmUnlocked = isSmallMultiplesUnlocked(panelMaturity?.phase ?? null);

  function setCompareZoomStage(next: CompareZoomStageIndex): void {
    compareZoomStage = next;
    writeCompareZoomStage(next);
  }

  function compareZoomOut(): void {
    setCompareZoomStage(clampZoomStageForWindow(compareZoomStage + 1, $analysisRange));
  }

  function compareZoomIn(): void {
    setCompareZoomStage(clampZoomStageForWindow(compareZoomStage - 1, $analysisRange));
  }

  onMount(() => {
    smoothing = readSmoothingPreference(typeof localStorage !== 'undefined' ? localStorage : null);
    compareMode = readCompareMode();
    compareSortMode = readCompareSortMode();
    compareCoincidenceHighlight = readCompareCoincidenceHighlight();
    compareLag1Highlight = readCompareLag1Highlight();
    compareOverlayHintDismissed = readCompareOverlayHintDismissed();
    sleepZeitversatz = readSleepZeitversatzPreference(
      typeof localStorage !== 'undefined' ? localStorage : null
    );
    restoreCompareLayers();
    mobileMedia = window.matchMedia?.(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`) ?? null;
    const updateCompactTrends = () => {
      compactTrends = mobileMedia?.matches ?? false;
    };
    updateCompactTrends();
    mobileMedia?.addEventListener('change', updateCompactTrends);
    // loadTrends runs via the auth-reactive block above (avoids racing hydrate).
    void loadInsights();
    const unregisterRefresh = registerPageRefresh(async () => {
      await Promise.all([loadTrends(), loadInsights()]);
      compareClusterRefreshToken += 1;
      scheduleSync();
    });
    return () => {
      trendsRequest.cancel();
      unregisterRefresh();
      mobileMedia?.removeEventListener('change', updateCompactTrends);
    };
  });
</script>

<svelte:head>
  <title>{$_('trends.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="trends screen-stack">
  <ScreenHeader title={$_('trends.title')} subtitle={$_('trends.subtitle')} sticky>
    <svelte:fragment slot="controls">
      {#if $auth.status === 'authenticated'}
        <TrendsAnalysisToolbar
          analysisRange={$analysisRange}
          analysisRangeOptions={rangeControlOptions}
          {activeTab}
          tabOptions={trendTabOptions}
          showCompareFilters={activeTab === 'compare'}
          embedCompareFilters={true}
          showRangeControl={true}
          on:rangeChange={(event) => {
            const nextDays = coerceTrendWindowDays(event.detail.value);
            if ($auth.status === 'authenticated')
              trendWindowPreference.select($auth.user.id, nextDays);
            void loadTrends(nextDays);
          }}
          on:tabChange={(event) => {
            activeTab = event.detail.value as TrendTab;
            void loadTrends();
          }}
        >
          <svelte:fragment slot="compare-filters">
            {#if compactTrends}
              <TrendsCompareQuickFilters
                {selectedCategory}
                on:categoryChange={(event) => {
                  selectedCategory = event.detail.category;
                  void loadTrends();
                }}
                on:openSettings={() => (compareSettingsOpen = true)}
              />
            {:else}
              <TrendsCompareFilters
                {smoothing}
                {smoothingAvailable}
                {metrics}
                {selectedCategory}
                {sleepZeitversatz}
                on:smoothingChange={(event) => setSmoothing(event.detail.value)}
                on:metricToggle={(event) => toggleMetric(event.detail.metric)}
                on:sleepZeitversatzChange={(event) => {
                  sleepZeitversatz = event.detail.value;
                  writeSleepZeitversatzPreference(
                    typeof localStorage !== 'undefined' ? localStorage : null,
                    event.detail.value
                  );
                }}
                on:categoryChange={(event) => {
                  selectedCategory = event.detail.category;
                  void loadTrends();
                }}
              />
            {/if}
          </svelte:fragment>
        </TrendsAnalysisToolbar>
      {/if}
    </svelte:fragment>
  </ScreenHeader>
  <TrendWindowSaveStatus />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('trends.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    {#if error}
      <InlineAlert variant="error" message={error} />
    {/if}

    {#if activeTab === 'compare' && topInsight}
      <AnalysisCrossLink insight={topInsight} direction="to-insights" />
    {/if}

    {#if activeTab === 'compare'}
      <div id="mobile-trends-detail" class="trends__detail" data-testid="mobile-trends-detail">
        <div
          class="trends__panel trends__panel--compare"
          role="tabpanel"
          aria-label={$_('trends.tabs.compare')}
        >
          <TrendsComparePanel
            points={displayTimeseries?.points ?? []}
            range={displayRange}
            windowDays={$analysisRange}
            enabled={metrics}
            markers={changepointMarkers}
            tagHeatmap={heatmap}
            {symptomHeatmap}
            {workContextHeatmap}
            showTags={showTagRows}
            showSymptoms={showSymptomRows}
            showWorkContexts={showWorkContextRows}
            {loading}
            pruneSparseAxes
            compactChrome={compactTrends}
            clusterRefreshToken={compareClusterRefreshToken}
            bind:clustersAvailableBinding={compareClustersAvailable}
            bind:focusedClusterId={compareFocusedClusterId}
            bind:zoomStage={compareZoomStage}
            bind:tagClusterLabelsBinding={compareTagClusterLabels}
            esmUnlocked={compareEsmUnlocked}
            bind:mode={compareMode}
            bind:sortMode={compareSortMode}
            bind:coincidenceHighlight={compareCoincidenceHighlight}
            bind:lag1Highlight={compareLag1Highlight}
            bind:overlayHintDismissed={compareOverlayHintDismissed}
            bind:overlayAvailabilityBinding={compareOverlayAvailability}
            noteDates={noteEntryDates}
            on:selectDate={(event) => void openHistory(event.detail.date)}
            on:layerChange={(event) => setCompareLayers(event.detail)}
            on:checkQuestion={(event) => {
              compareEsmWindows = event.detail.windows;
              compareEsmPartner = event.detail.partner ?? null;
              compareEsmPartnerDates = event.detail.partnerPresenceDates ?? [];
              compareEsmOpen = true;
            }}
          />
        </div>
        <TrendsHealthContext {healthContext} maturity={panelMaturity} {cycleEntries} />
      </div>

      <TrendsCompareSettingsSheet
        open={compactTrends && compareSettingsOpen}
        {smoothing}
        {smoothingAvailable}
        {metrics}
        {selectedCategory}
        {sleepZeitversatz}
        showTags={showTagRows}
        showSymptoms={showSymptomRows}
        showWorkContexts={showWorkContextRows}
        mode={compareMode}
        sortMode={compareSortMode}
        clustersAvailable={compareClustersAvailable}
        focusedClusterId={compareFocusedClusterId}
        tagClusterLabels={compareTagClusterLabels}
        zoomStage={compareZoomStage}
        windowDays={$analysisRange}
        rangeOptions={rangeControlOptions}
        coincidenceHighlight={compareCoincidenceHighlight}
        lag1Highlight={compareLag1Highlight}
        overlayAvailability={compareOverlayAvailability}
        overlayHintDismissed={compareOverlayHintDismissed}
        on:close={() => (compareSettingsOpen = false)}
        on:focusClusterChange={(event) => {
          compareFocusedClusterId = event.detail.clusterId;
        }}
        on:zoomIn={compareZoomIn}
        on:zoomOut={compareZoomOut}
        on:rangeChange={(event) => {
          const nextDays = coerceTrendWindowDays(event.detail.value);
          if ($auth.status === 'authenticated')
            trendWindowPreference.select($auth.user.id, nextDays);
          void loadTrends(nextDays);
        }}
        on:coincidenceChange={(event) => {
          compareCoincidenceHighlight = event.detail.value;
          writeCompareCoincidenceHighlight(event.detail.value);
        }}
        on:lag1Change={(event) => {
          compareLag1Highlight = event.detail.value;
          writeCompareLag1Highlight(event.detail.value);
        }}
        on:overlayHintDismiss={() => {
          compareOverlayHintDismissed = true;
          writeCompareOverlayHintDismissed(true);
        }}
        on:smoothingChange={(event) => setSmoothing(event.detail.value)}
        on:metricToggle={(event) => toggleMetric(event.detail.metric)}
        on:sleepZeitversatzChange={(event) => {
          sleepZeitversatz = event.detail.value;
          writeSleepZeitversatzPreference(
            typeof localStorage !== 'undefined' ? localStorage : null,
            event.detail.value
          );
        }}
        on:categoryChange={(event) => {
          selectedCategory = event.detail.category;
          void loadTrends();
        }}
        on:layerChange={(event) => setCompareLayers(event.detail)}
        on:modeChange={(event) => {
          compareMode = event.detail.value;
          writeCompareMode(event.detail.value);
        }}
        on:sortChange={(event) => {
          compareSortMode = event.detail.value;
          writeCompareSortMode(event.detail.value);
        }}
      />
    {:else}
      <div class="trends__panel" role="tabpanel" aria-label={$_('trends.tabs.habits')}>
        <HabitsPanel
          habits={habitStats}
          tags={habitTags}
          availableTags={allTags}
          {heatmap}
          window={habitWindow}
          {loading}
          on:selectDate={(event) => void openHistory(event.detail.date)}
          on:habitSetup={() => void loadTrends()}
        />
      </div>
    {/if}

    <EntryHistorySheet
      open={historyOpen}
      date={historyDate}
      loading={historyLoading}
      error={historyError}
      details={historyDetails}
      on:close={() => (historyOpen = false)}
    />

    <EventAlignedSmallMultiplesSheet
      open={compareEsmOpen}
      events={compareEsmWindows}
      partner={compareEsmPartner}
      partnerPresenceDates={compareEsmPartnerDates}
      points={displayTimeseries?.points ?? []}
      metric="mood_avg"
      phase={panelMaturity?.phase ?? null}
      on:close={() => {
        compareEsmOpen = false;
        compareEsmWindows = [];
        compareEsmPartner = null;
        compareEsmPartnerDates = [];
      }}
    />
  {/if}
</main>

<style>
  .trends {
    width: min(100%, 76rem);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
  }

  .trends__panel {
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
    min-width: 0;
  }

  .trends__panel--compare {
    padding: 0;
    overflow: hidden;
  }

  .trends__detail {
    display: grid;
    gap: var(--space-3);
  }
</style>
