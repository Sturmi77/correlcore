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
</script>

<section class="daily-brief" data-testid="home-daily-brief" aria-busy={loading}>
  <header class="daily-brief__header">
    <div>
      <p>{$_('home.brief.label')}</p>
      <h2>{$_('home.brief.heading')}</h2>
    </div>
  </header>

  <div class="daily-brief__insight">
    {#if latestInsight}
      <strong>{latestInsight.subject_label ?? latestInsight.metric}</strong>
      <p>{latestInsight.statement ?? $_('home.brief.insight_fallback')}</p>
    {:else if phaseLabel}
      <strong>{phaseLabel}</strong>
      <p>{$_('home.brief.phase_fallback')}</p>
    {:else}
      <strong>{$_('home.brief.collecting_title')}</strong>
      <p>{$_('home.brief.collecting_body')}</p>
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
</section>

<style>
  .daily-brief {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .daily-brief__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: flex-start;
  }

  .daily-brief__header p,
  .daily-brief__header h2,
  .daily-brief__insight p,
  .daily-brief__facts {
    margin: 0;
  }

  .daily-brief__header p {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .daily-brief__header h2 {
    margin-top: var(--space-1);
    font-size: var(--text-lg);
  }

  .daily-brief__header a {
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 700;
    white-space: nowrap;
  }

  .daily-brief__insight {
    display: grid;
    gap: var(--space-1);
  }

  .daily-brief__insight strong {
    font-size: var(--text-base);
  }

  .daily-brief__insight p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
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

  @media (max-width: 520px) {
    .daily-brief__header {
      flex-direction: column;
    }

    .daily-brief__facts {
      grid-template-columns: 1fr;
    }
  }
</style>
