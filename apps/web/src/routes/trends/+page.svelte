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
  import { mockEntries } from '$lib/dev/mockEntries';
  import {
    mockEntryStreak,
    mockHabitTags,
    mockHabits,
    mockSymptomHeatmap,
    mockTagHeatmap,
    mockTimeseries,
  } from '$lib/dev/mockTrends';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { analysisRange, setAnalysisRange } from '$lib/stores/analysisRange';
  import { insightStore, loadInsights } from '$lib/stores/insights';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
  import { smoothTimeseriesPoints } from '$lib/utils/charts';
  import { rangeToDays, rangeToHabitWindow } from '$lib/utils/trendsRange';
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
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import TabBar, { type TabBarOption } from '$lib/components/common/TabBar.svelte';
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
  let compactTrends = false;
  let mobileMedia: MediaQueryList | null = null;

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

  async function loadTrends(rangeOverride?: TimeseriesRange): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    const activeRange = rangeOverride ?? range;
    loading = true;
    error = '';
    try {
      if ($devForceVisualizations) {
        timeseries = { ...mockTimeseries, range: activeRange };
        heatmap = mockTagHeatmap;
        symptomHeatmap = mockSymptomHeatmap;
        streak = mockEntryStreak;
        habitStats = mockHabits.map((habit) => ({
          ...habit,
          window: rangeToHabitWindow(activeRange),
        }));
        habitTags = mockHabitTags;
        allTags = mockHabitTags;
        cycleEntries = mockEntries.filter((entry) => entry.cycle_day !== null);
        return;
      }

      const habitWindow = rangeToHabitWindow(activeRange);
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

  function setCompareLayers(next: { showTags: boolean; showSymptoms: boolean }): void {
    showTagRows = next.showTags;
    showSymptomRows = next.showSymptoms;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(COMPARE_LAYERS_STORAGE_KEY, JSON.stringify(next));
    }
  }

  function restoreCompareLayers(): void {
    if (typeof localStorage === 'undefined') return;
    try {
      const raw = localStorage.getItem(COMPARE_LAYERS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<{ showTags: boolean; showSymptoms: boolean }>;
      if (typeof parsed.showTags === 'boolean') showTagRows = parsed.showTags;
      if (typeof parsed.showSymptoms === 'boolean') showSymptomRows = parsed.showSymptoms;
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
        historyDetails = mockEntries
          .filter((entry) => entry.entry_date === date)
          .map((entry) => ({
            entry,
            tags: ['Focus work'],
            symptoms: [],
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
    <div class="trends__sticky-toolbar" data-testid="trends-sticky-toolbar">
      <SegmentedControl
        value={$analysisRange}
        options={rangeControlOptions}
        ariaLabel={$_('trends.controls')}
        testId="trends-range-control"
        on:change={(event) => {
          const nextRange = event.detail.value as TimeseriesRange;
          setAnalysisRange(nextRange);
          void loadTrends(nextRange);
        }}
      />
    </div>

    <TabBar
      value={activeTab}
      options={trendTabOptions}
      ariaLabel={$_('trends.tabs.label')}
      testId="trends-tabs"
      on:change={(event) => {
        activeTab = event.detail.value as TrendTab;
        void loadTrends();
      }}
    />

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
        <section class="trends__detail-controls" aria-label={$_('trends.mobile.detail_filters')}>
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
        </section>
      {:else}
        <section class="trends__compare-filters" aria-label={$_('trends.controls')}>
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
        </section>
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
            showTags={showTagRows}
            showSymptoms={showSymptomRows}
            {loading}
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

  .trends__sticky-toolbar {
    position: sticky;
    top: calc(var(--app-header-height, 0px) + var(--space-2));
    z-index: 3;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 94%, transparent);
    backdrop-filter: blur(14px);
  }

  .trends__compare-filters {
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
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

  .trends__detail-controls {
    padding-block: var(--space-3);
    border-block: 1px solid var(--color-border);
  }

  @media (max-width: 640px) {
    .trends__sticky-toolbar {
      position: static;
    }
  }
</style>
