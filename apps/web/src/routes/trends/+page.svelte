<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import {
    fetchEntryStreak,
    fetchTagHeatmap,
    fetchTimeseries,
    type EntryStreakResponse,
    type TagHeatmapResponse,
    type TimeseriesRange,
    type TimeseriesResponse,
  } from '$lib/api/stats';
  import type { MetricKey } from '$lib/utils/charts';
  import type { TagCategory } from '$lib/api/tags';
  import { TAG_CATEGORIES } from '$lib/api/tags';
  import MetricTimeseries from '$lib/components/trends/MetricTimeseries.svelte';
  import TagHeatmap from '$lib/components/trends/TagHeatmap.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';

  const metricLabels: Record<MetricKey, string> = {
    mood_avg: 'trends.metric.mood',
    energy_avg: 'trends.metric.energy',
    stress_avg: 'trends.metric.stress',
  };

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

  async function loadTrends(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = '';
    try {
      const [nextTimeseries, nextHeatmap, nextStreak] = await Promise.all([
        fetchTimeseries(range),
        fetchTagHeatmap(selectedCategory === 'all' ? {} : { category: selectedCategory }),
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

  $: if ($auth.status === 'authenticated' && timeseries && timeseries.range !== range && !loading) {
    void loadTrends();
  }

  onMount(() => {
    void loadTrends();
  });
</script>

<svelte:head>
  <title>{$_('trends.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="trends">
  <header class="trends__top">
    <a class="btn btn-sm variant-ghost-surface" href="/">{$_('nav.home')}</a>
    <ThemeToggle testId="trends-theme-toggle" />
  </header>

  <section class="trends__intro">
    <div>
      <h1>{$_('trends.title')}</h1>
      <p>{$_('trends.subtitle')}</p>
    </div>
    <a class="btn btn-sm variant-soft-primary" href="/settings">{$_('nav.settings')}</a>
  </section>

  {#if $auth.status !== 'authenticated'}
    <section class="trends__panel">
      <p>{$_('trends.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else}
    <section class="trends__controls" aria-label={$_('trends.controls')}>
      <div class="trends__segments">
        {#each ['week', 'month', 'year'] as option}
          <button
            type="button"
            class:active={range === option}
            on:click={() => {
              range = option as TimeseriesRange;
              void loadTrends();
            }}
          >
            {$_(`trends.range.${option}`)}
          </button>
        {/each}
      </div>

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
    </section>

    {#if error}
      <p class="trends__error" role="alert">{error}</p>
    {/if}

    <section class="trends__panel">
      <MetricTimeseries points={timeseries?.points ?? []} {range} enabled={metrics} {loading} />
    </section>

    <section class="trends__streak" aria-label={$_('trends.streak.heading')}>
      <div>
        <span>{$_('trends.streak.current')}</span>
        <strong>{streak?.current_streak ?? '-'}</strong>
      </div>
      <div>
        <span>{$_('trends.streak.longest')}</span>
        <strong>{streak?.longest_streak ?? '-'}</strong>
      </div>
      <div>
        <span>{$_('trends.streak.total')}</span>
        <strong>{streak?.total_entry_days ?? '-'}</strong>
      </div>
    </section>

    <section class="trends__panel">
      <TagHeatmap {heatmap} {loading} />
    </section>
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

  .trends__top,
  .trends__intro,
  .trends__controls,
  .trends__streak {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .trends__intro h1 {
    margin: 0;
    font-size: var(--text-2xl, 1.5rem);
    font-weight: 700;
  }

  .trends__intro p {
    margin: 0.25rem 0 0;
    max-width: 42rem;
    opacity: 0.72;
  }

  .trends__panel,
  .trends__streak {
    padding: 1rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .trends__controls {
    flex-wrap: wrap;
  }

  .trends__segments {
    display: inline-flex;
    gap: 0.25rem;
    padding: 0.25rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface);
  }

  .trends__segments button {
    min-height: 44px;
    border: 0;
    border-radius: var(--radius-sm);
    padding: 0.45rem 0.7rem;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 0.86rem;
    cursor: pointer;
  }

  .trends__segments button.active {
    background: var(--color-primary);
    color: var(--color-text-inverse);
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

  .trends__streak {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .trends__streak div {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .trends__streak span {
    font-size: 0.78rem;
    opacity: 0.7;
  }

  .trends__streak strong {
    font-size: 1.55rem;
  }

  .trends__error {
    margin: 0;
    color: var(--color-error);
  }

  @media (max-width: 640px) {
    .trends {
      padding: 1rem;
    }

    .trends__intro,
    .trends__controls {
      align-items: stretch;
      flex-direction: column;
    }

    .trends__streak {
      grid-template-columns: 1fr;
    }
  }
</style>
