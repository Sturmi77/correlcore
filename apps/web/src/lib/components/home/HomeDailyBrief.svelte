<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
  import { topInsightLabel } from '$lib/utils/analysisCrossLinks';
  import {
    maturityProgressMessage,
    maturityProgressPercent,
  } from '$lib/utils/insightMaturityProgress';
  import { rankInsights } from '$lib/utils/insightRanking';

  export let entries: EntryResponse[] = [];
  export let latestInsight: InsightResponse | null = null;
  export let maturity: InsightMaturity | null = null;
  export let loading = false;

  $: rankedInsights = latestInsight ? rankInsights([latestInsight]) : [];
  $: topInsight = rankedInsights[0] ?? null;
  $: phaseLabel = maturity ? $_(`maturity.${maturity.phase}.label`) : null;
  $: milestoneProgress = maturity ? maturityProgressMessage(maturity, $_) : null;
  $: milestonePercent = maturity ? maturityProgressPercent(maturity) : 0;
  $: showMilestoneProgress = Boolean(maturity && maturity.phase !== 'robust');
  $: showWeeklyBridge = Boolean(
    latestInsight || (maturity && maturity.phase !== 'collecting') || entries.length >= 3
  );
  $: insightBridgePreview = latestInsight ? topInsightLabel(latestInsight) : null;
  $: trendsBridgePreview = insightBridgePreview;
  $: topInsightConfidence =
    topInsight?.confidence != null ? Math.round(topInsight.confidence * 100) : null;
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

    {#if milestoneProgress}
      <p class="daily-brief__milestone" data-testid="home-brief-milestone-progress">
        {milestoneProgress}
      </p>
      {#if showMilestoneProgress}
        <div
          class="daily-brief__meter"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={milestonePercent}
          aria-label={$_('maturity.journey.progress_aria')}
        >
          <span style={`width: ${milestonePercent}%`}></span>
        </div>
      {/if}
    {/if}
  </div>

  <section class="daily-brief__top-insight" data-testid="home-brief-top-insight" aria-live="polite">
    <p class="daily-brief__top-insight-label">{$_('home.brief.top_insight')}</p>
    {#if topInsight}
      <p class="daily-brief__top-insight-statement">
        {topInsight.statement ?? topInsight.subject_label ?? topInsight.metric}
      </p>
      {#if topInsightConfidence != null}
        <p class="daily-brief__top-insight-confidence">
          {$_('home.brief.top_insight_confidence', { values: { value: topInsightConfidence } })}
        </p>
      {/if}
    {:else}
      <p class="daily-brief__top-insight-fallback">{$_('home.brief.top_insight_fallback')}</p>
    {/if}
  </section>

  {#if showWeeklyBridge}
    <nav
      class="daily-brief__bridge"
      aria-label={$_('home.brief.bridge_label')}
      data-testid="home-weekly-bridge"
    >
      <a href="/insights" data-testid="home-bridge-insights">
        <span class="daily-brief__bridge-label">{$_('home.explore_insights')}</span>
        {#if insightBridgePreview}
          <span class="daily-brief__bridge-preview">{insightBridgePreview}</span>
        {/if}
      </a>
      <a href="/trends" data-testid="home-bridge-trends">
        <span class="daily-brief__bridge-label">{$_('home.view_trends')}</span>
        {#if trendsBridgePreview}
          <span class="daily-brief__bridge-preview">{trendsBridgePreview}</span>
        {/if}
      </a>
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
  .daily-brief__top-insight p {
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

  .daily-brief__statement,
  .daily-brief__milestone {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.55;
    max-width: 42rem;
  }

  .daily-brief__milestone {
    font-weight: 650;
    color: var(--color-text);
  }

  .daily-brief__meter {
    height: 0.35rem;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-border) 70%, transparent);
    overflow: hidden;
  }

  .daily-brief__meter span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
  }

  .daily-brief__top-insight {
    display: grid;
    gap: var(--space-2);
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
  }

  .daily-brief__top-insight-label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .daily-brief__top-insight-statement {
    font-size: var(--text-sm);
    line-height: 1.55;
    font-weight: 600;
  }

  .daily-brief__top-insight-confidence,
  .daily-brief__top-insight-fallback {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.45;
  }

  .daily-brief__bridge {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
    padding-top: var(--space-1);
    border-top: 1px solid var(--color-border);
  }

  .daily-brief__bridge a {
    display: grid;
    gap: var(--space-1);
    min-height: 44px;
    padding: var(--space-2) var(--space-3);
    border: 1px solid color-mix(in srgb, var(--color-primary) 20%, transparent);
    border-radius: var(--radius-sm);
    color: var(--color-primary);
    text-decoration: none;
    background: var(--color-surface);
  }

  .daily-brief__bridge-label {
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .daily-brief__bridge-preview {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  .daily-brief__bridge a:hover,
  .daily-brief__bridge a:focus-visible {
    border-color: color-mix(in srgb, var(--color-primary) 35%, transparent);
    background: var(--color-primary-highlight);
  }

  @media (max-width: 520px) {
    .daily-brief__bridge {
      grid-template-columns: 1fr;
    }
  }
</style>
