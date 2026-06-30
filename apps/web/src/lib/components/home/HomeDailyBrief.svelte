<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';

  export let entries: EntryResponse[] = [];
  export let latestInsight: InsightResponse | null = null;
  export let maturity: InsightMaturity | null = null;
  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let loading = false;

  function moodDelta(list: readonly EntryResponse[]): number | null {
    const dayEntries = list
      .filter((entry) => entry.slot === 'day')
      .sort((a, b) => a.entry_date.localeCompare(b.entry_date));
    if (dayEntries.length < 2) return null;
    return dayEntries[dayEntries.length - 1].mood_score - dayEntries[0].mood_score;
  }

  function topTagLabel(heatmap: TagHeatmapResponse | null): string | null {
    const top = heatmap?.tags
      .map((tag) => ({
        name: tag.name,
        count: tag.days.reduce((sum, day) => sum + day.count, 0),
      }))
      .filter((tag) => tag.count > 0)
      .sort((a, b) => b.count - a.count)[0];
    return top ? `${top.name} (${top.count})` : null;
  }

  function topSymptomLabel(heatmap: SymptomHeatmapResponse | null): string | null {
    const top = heatmap?.symptoms
      .map((symptom) => ({
        name: symptom.name,
        count: symptom.days.reduce((sum, day) => sum + day.count, 0),
        maxIntensity: Math.max(0, ...symptom.days.map((day) => day.max_intensity)),
      }))
      .filter((symptom) => symptom.count > 0)
      .sort((a, b) => b.count - a.count || b.maxIntensity - a.maxIntensity)[0];
    return top ? `${top.name} (${top.count})` : null;
  }

  $: delta = moodDelta(entries);
  $: deltaLabel =
    delta === null
      ? $_('home.brief.delta_empty')
      : delta > 0
        ? $_('home.brief.delta_up', { values: { value: delta } })
        : delta < 0
          ? $_('home.brief.delta_down', { values: { value: Math.abs(delta) } })
          : $_('home.brief.delta_flat');
  $: tagLabel = topTagLabel(tagHeatmap);
  $: symptomLabel = topSymptomLabel(symptomHeatmap);
  $: phaseLabel = maturity ? $_(`maturity.${maturity.phase}.label`) : null;
  $: showWeeklyBridge = Boolean(
    latestInsight || (maturity && maturity.phase !== 'collecting') || entries.length >= 3
  );
</script>

<section class="daily-brief" data-testid="home-daily-brief" aria-busy={loading}>
  <header class="daily-brief__header">
    <p>{$_('home.brief.label')}</p>
  </header>

  <div class="daily-brief__lead">
    {#if latestInsight}
      <h2 class="daily-brief__title">{latestInsight.subject_label ?? latestInsight.metric}</h2>
      <p class="daily-brief__statement">
        {latestInsight.statement ?? $_('home.brief.insight_fallback')}
      </p>
    {:else if phaseLabel}
      <h2 class="daily-brief__title">{phaseLabel}</h2>
      <p class="daily-brief__statement">{$_('home.brief.phase_fallback')}</p>
    {:else}
      <h2 class="daily-brief__title">{$_('home.brief.collecting_title')}</h2>
      <p class="daily-brief__statement">{$_('home.brief.collecting_body')}</p>
    {/if}
  </div>

  <dl class="daily-brief__facts">
    <div>
      <dt>{$_('home.brief.mood_delta')}</dt>
      <dd>{deltaLabel}</dd>
    </div>
    <div>
      <dt>{$_('home.brief.top_tag')}</dt>
      <dd>{tagLabel ?? $_('home.brief.none')}</dd>
    </div>
    <div>
      <dt>{$_('home.brief.top_symptom')}</dt>
      <dd>{symptomLabel ?? $_('home.brief.none')}</dd>
    </div>
  </dl>

  {#if showWeeklyBridge}
    <nav class="daily-brief__bridge" aria-label={$_('home.brief.bridge_label')} data-testid="home-weekly-bridge">
      <a href="/insights" data-testid="home-bridge-insights">{$_('home.explore_insights')}</a>
      <a href="/trends" data-testid="home-bridge-trends">{$_('home.view_trends')}</a>
    </nav>
  {/if}
</section>

<style>
  .daily-brief {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-5);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .daily-brief__header p,
  .daily-brief__lead p,
  .daily-brief__facts {
    margin: 0;
  }

  .daily-brief__header p {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .daily-brief__lead {
    display: grid;
    gap: var(--space-2);
  }

  .daily-brief__title {
    margin: 0;
    font-size: clamp(1.125rem, 2.5vw, 1.35rem);
    font-weight: 650;
    line-height: 1.25;
  }

  .daily-brief__statement {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.55;
    max-width: 42rem;
  }

  .daily-brief__facts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .daily-brief__facts div {
    display: grid;
    gap: var(--space-1);
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
  }

  .daily-brief__facts dt {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .daily-brief__facts dd {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .daily-brief__bridge {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    padding-top: var(--space-1);
    border-top: 1px solid var(--color-border);
  }

  .daily-brief__bridge a {
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 600;
    text-decoration: none;
  }

  .daily-brief__bridge a:hover {
    text-decoration: underline;
  }

  @media (max-width: 520px) {
    .daily-brief__facts {
      grid-template-columns: 1fr;
    }
  }
</style>
