<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
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
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
  import { smoothTimeseriesPoints } from '$lib/utils/charts';
  import { rangeToDays, rangeToHabitWindow } from '$lib/utils/trendsRange';
  import {
    buildWorkContextHeatmap,
    type WorkContextHeatmapResponse,
  } from '$lib/utils/workContextHeatmap';
  import TrendsAnalysisToolbar from '$lib/components/trends/TrendsAnalysisToolbar.svelte';
  import TrendsComparePanel from '$lib/components/trends/TrendsComparePanel.svelte';
  import TrendsCompareFilters from '$lib/components/trends/TrendsCompareFilters.svelte';
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
  let workContextHeatmap: WorkContextHeatmapResponse | null = null;
  let metrics: Record<MetricKey, boolean> = {
    mood_avg: true,
    energy_avg: true,
    stress_avg: true,
  };
  let loading = false;
  let error = '';
  let historyOpen = false;
  let historyDate = '';
  let historyLoading = false;
  let historyError = '';
  let historyDetails: EntryHistoryDetail[] = [];
  let smoothing = false;
  let showTagRows = true;
  let showSymptomRows = false;
  let showWorkContextRows = true;
  let compactTrends = false;
  let mobileMedia: MediaQueryList | null = null;
  let activeDevFixtureKey = '';

  const SMOOTHING_STORAGE_KEY = 'cc_trend_smooth';
  const COMPARE_LAYERS_STORAGE_KEY = 'cc_trend_compare_layers';

  $: range = $analysisRange;

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
    const activeRange = rangeOverride ?? range;
    const habitWindow = rangeToHabitWindow(activeRange);
    loading = true;
    error = '';
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
        workContextHeatmap = buildWorkContextHeatmap(fixture.entries, dateWindow(activeRange));
        return;
      }

      const { start_date, end_date } = dateWindow(
        activeRange,
        activeTab === 'habits' ? habitWindow : undefined
      );
      const [
        nextTimeseries,
        nextHeatmap,
        nextSymptomHeatmap,
        nextStreak,
        nextEntries,
        nextHabitStats,
        nextTags,
      ] = await Promise.all([
        fetchTimeseries(activeRange),
        fetchTagHeatmap({
          start_date,
          end_date,
          ...(activeTab === 'compare' && selectedCategory !== 'all'
            ? { category: selectedCategory }
            : {}),
        }),
        activeTab === 'compare'
          ? fetchSymptomHeatmap({ start_date, end_date })
          : Promise.resolve(symptomHeatmap),
        fetchEntryStreak(),
        listEntries({ start_date, end_date, limit: 365 }),
        activeTab === 'habits' ? listHabits(habitWindow) : Promise.resolve({ habits: habitStats }),
        activeTab === 'habits' ? listVisibleTags() : Promise.resolve(habitTags),
      ]);
      timeseries = nextTimeseries;
      heatmap = nextHeatmap;
      symptomHeatmap = nextSymptomHeatmap;
      streak = nextStreak;
      habitStats = nextHabitStats.habits;
      allTags = nextTags;
      habitTags = nextTags.filter((tag) => tag.habit_type !== 'none');
      cycleEntries = nextEntries.filter((entry) => entry.cycle_day !== null);
      workContextHeatmap = buildWorkContextHeatmap(nextEntries, { start_date, end_date });
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      loading = false;
    }
  }

  function toggleMetric(metric: MetricKey): void {
    metrics = { ...metrics, [metric]: !metrics[metric] };
  }

  function setSmoothing(value: boolean): void {
    smoothing = value;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SMOOTHING_STORAGE_KEY, value ? 'true' : 'false');
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

  $: if (
    $auth.status === 'authenticated' &&
    timeseries &&
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
  $: rangeControlOptions = rangeOptions.map(
    (option): SegmentedControlOption => ({
      id: option.id,
      label: $_(option.label),
      testId: `trends-range-${option.id}`,
    })
  );
  $: trendTabOptions = tabs.map(
    (tab): TabBarOption => ({
      id: tab.id,
      label: $_(tab.label),
      testId: `trends-tab-${tab.id}`,
    })
  );
  $: smoothingAvailable = range !== 'week';
  $: displayTimeseries =
    timeseries && smoothing && smoothingAvailable
      ? { ...timeseries, points: smoothTimeseriesPoints(timeseries.points) }
      : timeseries;
  $: topInsight = $insightStore.latest;

  onMount(() => {
    smoothing = localStorage.getItem(SMOOTHING_STORAGE_KEY) === 'true';
    restoreCompareLayers();
    mobileMedia = window.matchMedia?.(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`) ?? null;
    const updateCompactTrends = () => {
      compactTrends = mobileMedia?.matches ?? false;
    };
    updateCompactTrends();
    mobileMedia?.addEventListener('change', updateCompactTrends);
    void loadTrends();
    void loadInsights();
    return () => mobileMedia?.removeEventListener('change', updateCompactTrends);
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
            {range}
            enabled={metrics}
            tagHeatmap={heatmap}
            {symptomHeatmap}
            {workContextHeatmap}
            showTags={showTagRows}
            showSymptoms={showSymptomRows}
            showWorkContexts={showWorkContextRows}
            {loading}
            pruneSparseAxes={compactTrends}
            on:selectDate={(event) => void openHistory(event.detail.date)}
            on:layerChange={(event) => setCompareLayers(event.detail)}
          />
        </div>
        <TrendsHealthContext {streak} {cycleEntries} />
      </div>
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
