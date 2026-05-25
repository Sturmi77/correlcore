<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listEntries, type EntryResponse } from '$lib/api/entries';
  import {
    fetchEntryStreak,
    fetchTagHeatmap,
    fetchTimeseries,
    type EntryStreakResponse,
    type TagHeatmapResponse,
    type TimeseriesRange,
    type TimeseriesResponse,
  } from '$lib/api/stats';
  import { listSymptomsForEntry, listVisibleSymptoms } from '$lib/api/symptoms';
  import { listTagsForEntry } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';
  import type { TagCategory } from '$lib/api/tags';
  import { TAG_CATEGORIES } from '$lib/api/tags';
  import { mockEntries } from '$lib/dev/mockEntries';
  import { mockEntryStreak, mockTagHeatmap, mockTimeseries } from '$lib/dev/mockTrends';
  import { devForceVisualizations } from '$lib/stores/devMode';
  import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
  import MetricTimeseries from '$lib/components/trends/MetricTimeseries.svelte';
  import TagHeatmap from '$lib/components/trends/TagHeatmap.svelte';
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

  type TrendTab = 'mood' | 'activities' | 'health';

  const metricLabels: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
  };

  const rangeOptions: { id: TimeseriesRange; label: string; days: number }[] = [
    { id: 'week', label: 'trends.range.week', days: 7 },
    { id: 'month', label: 'trends.range.month', days: 30 },
    { id: 'quarter', label: 'trends.range.quarter', days: 90 },
    { id: 'year', label: 'trends.range.year', days: 365 },
  ];

  const tabs: { id: TrendTab; label: string }[] = [
    { id: 'mood', label: 'trends.tabs.mood' },
    { id: 'activities', label: 'trends.tabs.activities' },
    { id: 'health', label: 'trends.tabs.health' },
  ];

  let activeTab: TrendTab = 'mood';
  let range: TimeseriesRange = 'week';
  let selectedCategory: TagCategory | 'all' = 'all';
  let timeseries: TimeseriesResponse | null = null;
  let heatmap: TagHeatmapResponse | null = null;
  let streak: EntryStreakResponse | null = null;
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

  function dateWindow(): { start_date: string; end_date: string } {
    const option = rangeOptions.find((item) => item.id === range) ?? rangeOptions[0];
    const end_date = localIsoDate(new Date());
    return { start_date: shiftIsoDate(end_date, -(option.days - 1)), end_date };
  }

  async function loadTrends(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = '';
    try {
      if ($devForceVisualizations) {
        timeseries = { ...mockTimeseries, range };
        heatmap = mockTagHeatmap;
        streak = mockEntryStreak;
        return;
      }

      const { start_date, end_date } = dateWindow();
      const [nextTimeseries, nextHeatmap, nextStreak] = await Promise.all([
        fetchTimeseries(range),
        fetchTagHeatmap({
          start_date,
          end_date,
          ...(selectedCategory === 'all' ? {} : { category: selectedCategory }),
        }),
        fetchEntryStreak(),
      ]);
      timeseries = nextTimeseries;
      heatmap = nextHeatmap;
      streak = nextStreak;
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
    } finally {
      loading = false;
    }
  }

  function toggleMetric(metric: MetricKey): void {
    metrics = { ...metrics, [metric]: !metrics[metric] };
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

  $: if ($auth.status === 'authenticated' && timeseries && timeseries.range !== range && !loading) {
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

  onMount(() => {
    void loadTrends();
  });
</script>

<svelte:head>
  <title>{$_('trends.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="trends">
  <ScreenHeader title={$_('trends.title')} subtitle={$_('trends.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('trends.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <section class="trends__controls" aria-label={$_('trends.controls')}>
      <SegmentedControl
        value={range}
        options={rangeControlOptions}
        ariaLabel={$_('trends.controls')}
        testId="trends-range-control"
        on:change={(event) => {
          range = event.detail.value as TimeseriesRange;
          void loadTrends();
        }}
      />

      {#if activeTab === 'mood'}
        <div class="trends__metric-toggles">
          {#each Object.entries(metricLabels) as [key, label]}
            <label>
              <input
                type="checkbox"
                checked={metrics[key as MetricKey]}
                on:change={() => toggleMetric(key as MetricKey)}
              />
              {$_(label)}
            </label>
          {/each}
        </div>
      {:else if activeTab === 'activities'}
        <label class="trends__select">
          <span>{$_('trends.category')}</span>
          <select
            bind:value={selectedCategory}
            on:change={() => {
              void loadTrends();
            }}
          >
            <option value="all">{$_('trends.category_all')}</option>
            {#each TAG_CATEGORIES as category}
              <option value={category}>{$_(`tag.category.${category}`)}</option>
            {/each}
          </select>
        </label>
      {/if}
    </section>

    <TabBar
      value={activeTab}
      options={trendTabOptions}
      ariaLabel={$_('trends.tabs.label')}
      testId="trends-tabs"
      on:change={(event) => (activeTab = event.detail.value as TrendTab)}
    />

    {#if error}
      <InlineAlert variant="error" message={error} />
    {/if}

    {#if activeTab === 'mood'}
      <div class="trends__panel" role="tabpanel" aria-label={$_('trends.tabs.mood')}>
        <MetricTimeseries
          points={timeseries?.points ?? []}
          {range}
          enabled={metrics}
          {loading}
          on:selectDate={(event) => void openHistory(event.detail.date)}
        />
      </div>
    {:else if activeTab === 'activities'}
      <div class="trends__panel" role="tabpanel" aria-label={$_('trends.tabs.activities')}>
        <TagHeatmap
          {heatmap}
          {loading}
          on:selectDate={(event) => void openHistory(event.detail.date)}
        />
      </div>
    {:else}
      <div
        class="trends__panel trends__health"
        role="tabpanel"
        aria-label={$_('trends.tabs.health')}
      >
        <div>
          <h2>{$_('trends.health.heading')}</h2>
          <p>{$_('trends.health.body')}</p>
        </div>
        <section class="trends__consistency" aria-label={$_('trends.consistency.heading')}>
          <div>
            <span>{$_('trends.consistency.current')}</span>
            <strong>{streak?.current_streak ?? '-'}</strong>
          </div>
          <div>
            <span>{$_('trends.consistency.longest')}</span>
            <strong>{streak?.longest_streak ?? '-'}</strong>
          </div>
          <div>
            <span>{$_('trends.consistency.total')}</span>
            <strong>{streak?.total_entry_days ?? '-'}</strong>
          </div>
        </section>
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
    width: min(100%, 68rem);
    margin: 0 auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .trends__controls,
  .trends__consistency {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .trends__panel,
  .trends__consistency {
    padding: 1rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .trends__controls {
    flex-wrap: wrap;
  }

  .trends__metric-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: 0.86rem;
  }

  .trends__metric-toggles label,
  .trends__select {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }

  .trends__select span {
    font-size: 0.8rem;
    opacity: 0.72;
  }

  .trends__select select {
    min-height: 44px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: inherit;
    padding: 0 0.55rem;
  }

  .trends__consistency {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .trends__consistency div {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .trends__consistency span {
    font-size: 0.78rem;
    opacity: 0.7;
  }

  .trends__consistency strong {
    font-size: 1.55rem;
  }

  .trends__health {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .trends__health h2 {
    margin: 0;
    font-size: var(--text-lg);
  }

  .trends__health p {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
  }

  @media (max-width: 640px) {
    .trends {
      padding: 1rem;
    }

    .trends__controls {
      align-items: stretch;
      flex-direction: column;
    }

    .trends__consistency {
      grid-template-columns: 1fr;
    }
  }
</style>
