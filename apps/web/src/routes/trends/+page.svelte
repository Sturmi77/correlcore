<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import { hasNote } from '$lib/utils/noteSummary';
  import {
    fetchEntryStreak,
    fetchSymptomHeatmap,
    fetchTagHeatmap,
    fetchTimeseries,
    type EntryStreakResponse,
    type SymptomHeatmapResponse,
    type TagHeatmapResponse,
    type TimeseriesRange,
    type TimeseriesResponse,
  } from '$lib/api/stats';
  import { listHabits, type HabitStatsResponse } from '$lib/api/habits';
  import { listSymptomsForEntry, listVisibleSymptoms } from '$lib/api/symptoms';
  import { listTagsForEntry, listVisibleTags, type TagResponse } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';
  import type { TagCategory } from '$lib/api/tags';
  import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { analysisRange, setAnalysisRange } from '$lib/stores/analysisRange';
  import { insightStore, loadInsights } from '$lib/stores/insights';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';
  import { scheduleSync } from '$lib/offline/syncOrchestrator';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
  import { smoothTimeseriesPoints } from '$lib/utils/charts';
  import {
    rangeToDays,
    rangeToHabitWindow,
    readSmoothingPreference,
    smoothingWindowDays,
    TREND_SMOOTHING_STORAGE_KEY,
  } from '$lib/utils/trendsRange';
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
  import MobileTrendsSummary from '$lib/components/trends/MobileTrendsSummary.svelte';
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
  import {
    readCompareMode,
    readCompareSortMode,
    writeCompareMode,
    writeCompareSortMode,
    type CompareMode,
    type CompareSortMode,
  } from '$lib/utils/comparePanelSettings';

  type TrendTab = 'compare' | 'habits';

  const rangeOptions: { id: TimeseriesRange; label: string }[] = [
    { id: 'week', label: 'trends.range.week' },
    { id: 'month', label: 'trends.range.month' },
    { id: 'quarter', label: 'trends.range.quarter' },
    { id: 'year', label: 'trends.range.year' },
  ];

  const tabs: { id: TrendTab; label: string }[] = [
    { id: 'compare', label: 'trends.tabs.compare' },
    { id: 'habits', label: 'trends.tabs.habits' },
  ];

  let activeTab: TrendTab = 'compare';
  let selectedCategory: TagCategory | 'all' = 'all';
  let timeseries: TimeseriesResponse | null = null;
  let heatmap: TagHeatmapResponse | null = null;
  let symptomHeatmap: SymptomHeatmapResponse | null = null;
  let streak: EntryStreakResponse | null = null;
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
  let mobileMedia: MediaQueryList | null = null;
  let activeDevFixtureKey = '';

  const COMPARE_LAYERS_STORAGE_KEY = 'cc_trend_compare_layers';

  $: range = $analysisRange;
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

  async function loadTrends(rangeOverride?: TimeseriesRange): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    // Compare axis zoom (CAZ-0): always load a 365d / year window; range chips are hidden.
    const uiRange = rangeOverride ?? range;
    const activeRange: TimeseriesRange = activeTab === 'compare' ? 'year' : uiRange;
    const habitWindow = rangeToHabitWindow(uiRange);
    const compareWindowDays = activeTab === 'compare' ? 365 : undefined;
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
        streak = fixture.streak;
        habitStats = fixture.habitStats.map((habit) => ({ ...habit, window: habitWindow }));
        habitTags = fixture.habitTags;
        allTags = fixture.habitTags;
        cycleEntries = fixture.entries.filter((entry) => entry.cycle_day !== null);
        trendEntries = fixture.entries;
        workContextHeatmap = buildWorkContextHeatmap(
          fixture.entries,
          dateWindow(activeRange, compareWindowDays)
        );
        return;
      }

      const { start_date, end_date } = dateWindow(
        activeRange,
        activeTab === 'habits' ? habitWindow : compareWindowDays
      );
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
        streakResult,
        entriesResult,
        habitResult,
        tagsResult,
      ] = await Promise.allSettled([
        fetchTimeseries(activeRange),
        fetchTagHeatmap({
          start_date,
          end_date,
          ...(activeTab === 'compare' && selectedCategory !== 'all'
            ? { category: selectedCategory }
            : {}),
        }),
        symptomPromise,
        fetchEntryStreak(),
        listEntries({ start_date, end_date, limit: 365 }),
        activeTab === 'habits' ? listHabits(habitWindow) : Promise.resolve({ habits: habitStats }),
        activeTab === 'habits' ? listVisibleTags() : Promise.resolve(habitTags),
      ]);

      const coreFailed = [timeseriesResult, heatmapResult, streakResult, entriesResult].find(
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
      if (streakResult.status === 'fulfilled') streak = streakResult.value;
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
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      loading = false;
      trendsLoaded = true;
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
            tags: ['Focus work'],
            symptoms: fixture.symptomHeatmap.symptoms.map((symptom) => ({
              name: symptom.name,
              intensity: symptom.days.find((day) => day.date === date)?.max_intensity ?? 1,
            })),
            markers: entry.note_markers ?? [],
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
            markers: entry.note_markers ?? [],
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
  // Compare ignores analysisRange chips (fixed year window). Habits still sync to the control.
  $: if (
    $auth.status === 'authenticated' &&
    timeseries &&
    activeTab !== 'compare' &&
    timeseries.range !== $analysisRange &&
    !loading
  ) {
    void loadTrends($analysisRange);
  }
  $: habitWindow = rangeToHabitWindow(range);
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
  $: displayRange = (activeTab === 'compare' ? 'year' : range) as TimeseriesRange;
  $: displayTimeseries =
    timeseries && smoothing && smoothingAvailable
      ? {
          ...timeseries,
          points: smoothTimeseriesPoints(timeseries.points, smoothingWindowDays(displayRange)),
        }
      : timeseries;
  $: topInsight = $insightStore.latest;

  onMount(() => {
    smoothing = readSmoothingPreference(typeof localStorage !== 'undefined' ? localStorage : null);
    compareMode = readCompareMode();
    compareSortMode = readCompareSortMode();
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
      unregisterRefresh();
      mobileMedia?.removeEventListener('change', updateCompactTrends);
    };
  });
</script>

<svelte:head>
  <title>{$_('trends.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="trends screen-stack">
  <ScreenHeader title={$_('trends.title')} subtitle={$_('trends.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('trends.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <TrendsAnalysisToolbar
      analysisRange={$analysisRange}
      analysisRangeOptions={rangeControlOptions}
      {activeTab}
      tabOptions={trendTabOptions}
      showCompareFilters={activeTab === 'compare'}
      embedCompareFilters={!compactTrends}
      showRangeControl={activeTab !== 'compare'}
      on:rangeChange={(event) => {
        const nextRange = event.detail.value as TimeseriesRange;
        setAnalysisRange(nextRange);
        void loadTrends(nextRange);
      }}
      on:tabChange={(event) => {
        activeTab = event.detail.value as TrendTab;
        void loadTrends();
      }}
    >
      <svelte:fragment slot="compare-filters">
        <TrendsCompareFilters
          {smoothing}
          {smoothingAvailable}
          {metrics}
          {selectedCategory}
          on:smoothingChange={(event) => setSmoothing(event.detail.value)}
          on:metricToggle={(event) => toggleMetric(event.detail.metric)}
          on:categoryChange={(event) => {
            selectedCategory = event.detail.category;
            void loadTrends();
          }}
        />
      </svelte:fragment>
    </TrendsAnalysisToolbar>

    {#if error}
      <InlineAlert variant="error" message={error} />
    {/if}

    {#if activeTab === 'compare' && topInsight}
      <AnalysisCrossLink insight={topInsight} direction="to-insights" />
    {/if}

    {#if activeTab === 'compare'}
      {#if compactTrends}
        <TrendsCompareQuickFilters
          {metrics}
          {selectedCategory}
          on:metricToggle={(event) => toggleMetric(event.detail.metric)}
          on:categoryChange={(event) => {
            selectedCategory = event.detail.category;
            void loadTrends();
          }}
          on:openSettings={() => (compareSettingsOpen = true)}
        />
      {/if}

      {#if compactTrends}
        <MobileTrendsSummary
          points={displayTimeseries?.points ?? []}
          tagHeatmap={heatmap}
          {symptomHeatmap}
          {range}
          {loading}
        />
      {/if}

      <div id="mobile-trends-detail" class="trends__detail" data-testid="mobile-trends-detail">
        <div
          class="trends__panel trends__panel--compare"
          role="tabpanel"
          aria-label={$_('trends.tabs.compare')}
        >
          <TrendsComparePanel
            points={displayTimeseries?.points ?? []}
            range="year"
            enabled={metrics}
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
            bind:mode={compareMode}
            bind:sortMode={compareSortMode}
            noteDates={noteEntryDates}
            on:selectDate={(event) => void openHistory(event.detail.date)}
            on:layerChange={(event) => setCompareLayers(event.detail)}
          />
        </div>
        <TrendsHealthContext {streak} {cycleEntries} />
      </div>

      <TrendsCompareSettingsSheet
        open={compactTrends && compareSettingsOpen}
        {smoothing}
        {smoothingAvailable}
        {metrics}
        {selectedCategory}
        showTags={showTagRows}
        showSymptoms={showSymptomRows}
        showWorkContexts={showWorkContextRows}
        mode={compareMode}
        sortMode={compareSortMode}
        clustersAvailable={compareClustersAvailable}
        on:close={() => (compareSettingsOpen = false)}
        on:smoothingChange={(event) => setSmoothing(event.detail.value)}
        on:metricToggle={(event) => toggleMetric(event.detail.metric)}
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
