<script lang="ts">
  /**
   * /insights/signal/[id] — Ebene 2 verification surface (Phase 7 / ADR-0043).
   * Sentence → with/without (G2) → course/ESM → scatter (G1) behind disclosure.
   */
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import {
    fetchInsight,
    fetchInsightEventWindows,
    fetchInsightVerification,
    type InsightMaturity,
    type InsightResponse,
    type InsightVerificationResponse,
  } from '$lib/api/insights';
  import { listLatestInsights } from '$lib/api/insights';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import InsightEvidence from '$lib/components/insights/InsightEvidence.svelte';
  import WithWithoutDistribution from '$lib/components/insights/WithWithoutDistribution.svelte';
  import SignalScatter from '$lib/components/insights/SignalScatter.svelte';
  import EventAlignedSmallMultiplesSheet from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import type { EventWindow } from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
  import type { TimeseriesPoint } from '$lib/api/stats';
  import { insightMetricToChartKey, isExploreEventsSubject } from '$lib/utils/exploreEventWindows';
  import { isNullAssociation, parseWithWithoutView } from '$lib/utils/withWithoutDistribution';
  import { parseSameSituationView } from '$lib/utils/sameSituation';
  import { stripLegacyInsightStatementTails } from '$lib/utils/stripLegacyInsightStatementTails';
  import { isSmallMultiplesUnlocked } from '$lib/components/trends/smallMultiplesGate';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let insight: InsightResponse | null = null;
  let maturity: InsightMaturity | null = null;
  let verification: InsightVerificationResponse | null = null;
  let loading = true;
  let error: string | null = null;
  let showScatter = false;
  let showSameSituation = false;
  let esmOpen = false;
  let esmWindows: EventWindow[] = [];
  let esmPoints: TimeseriesPoint[] = [];
  let esmLag: number | null = null;
  let esmLoading = false;

  $: insightId = $page.params.id ?? '';
  $: withWithout = insight ? parseWithWithoutView(insight) : null;
  $: sameSituation = insight ? parseSameSituationView(insight) : null;
  $: isNull = insight ? isNullAssociation(insight) : false;
  $: title =
    insight?.subject_label && insight.metric
      ? `${insight.subject_label} → ${insight.metric}`
      : $_('insights.signal.title_fallback');
  $: canOpenEsm =
    Boolean(insight && isExploreEventsSubject(insight)) &&
    isSmallMultiplesUnlocked(maturity?.phase ?? null);
  $: showUncertaintyRibbon = maturity?.phase !== 'robust';

  async function load(): Promise<void> {
    if (!insightId) return;
    loading = true;
    error = null;
    try {
      const [detail, latest] = await Promise.all([
        fetchInsight(insightId),
        listLatestInsights({ limit: 1 }).catch(() => null),
      ]);
      insight = detail;
      maturity = latest?.insight_maturity ?? null;
      verification = await fetchInsightVerification(insightId, '90d').catch(() => null);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('insights.signal.error');
      insight = null;
      verification = null;
    } finally {
      loading = false;
    }
  }

  async function openEsm(): Promise<void> {
    if (!insight) return;
    esmOpen = true;
    esmLoading = true;
    try {
      const response = await fetchInsightEventWindows(insight.id, '90d');
      esmWindows = response.events.map((event) => ({
        onset: event.onset,
        label: event.label ?? undefined,
      }));
      esmPoints = response.points;
      esmLag = response.lag_days ?? null;
    } catch {
      esmWindows = [];
      esmPoints = [];
      esmLag = null;
    } finally {
      esmLoading = false;
    }
  }

  onMount(() => {
    if (!$auth.user) {
      void goto('/auth/login');
      return;
    }
    void load();
    return registerPageRefresh(() => void load());
  });
</script>

<svelte:head>
  <title>{title} - {$_('app.name')}</title>
</svelte:head>

<main class="signal-page screen-stack screen-stack--tight" data-testid="signal-detail-page">
  <ScreenHeader
    sticky
    {title}
    subtitle={isNull
      ? `${$_('insights.signal.subtitle')} · ${$_('insights.card.null_badge')}`
      : $_('insights.signal.subtitle')}
    back={{ href: '/insights', label: $_('insights.signal.back') }}
  />

  {#if loading}
    <p class="signal-page__status">{$_('insights.signal.loading')}</p>
  {:else if error}
    <InlineAlert variant="error">{error}</InlineAlert>
  {:else if insight}
    <section class="signal-page__card" data-testid="signal-statement">
      <p class="signal-page__statement">
        {stripLegacyInsightStatementTails(insight.statement) || $_('home.insight.empty_statement')}
      </p>
      <p class="signal-page__hint">{$_('insights.signal.non_causal')}</p>
      <InsightEvidence
        {maturity}
        confidenceScore={insight.confidence ?? 0}
        currentTier={insight.tier}
        entryCount={insight.sample_n ?? 0}
        showSample
      />
    </section>

    {#if withWithout}
      <section class="signal-page__card">
        <WithWithoutDistribution view={withWithout} />
      </section>
    {/if}

    {#if sameSituation}
      <section class="signal-page__card" data-testid="signal-same-situation">
        <button
          type="button"
          class="signal-page__chip"
          data-testid="signal-toggle-same-situation"
          aria-expanded={showSameSituation}
          on:click={() => (showSameSituation = !showSameSituation)}
        >
          {showSameSituation
            ? $_('insights.signal.same_situation_hide')
            : $_('insights.signal.same_situation_show')}
        </button>
        {#if showSameSituation}
          <p class="signal-page__means" data-testid="signal-same-situation-freq">
            {$_('insights.signal.same_work_context_freq', {
              values: {
                context: sameSituation.context,
                withGood: sameSituation.withGood,
                withN: sameSituation.withN,
                withoutGood: sameSituation.withoutGood,
                withoutN: sameSituation.withoutN,
                subject: insight.subject_label ?? '',
              },
            })}
          </p>
          {#if sameSituation.effectSurvives === false}
            <p class="signal-page__hint" data-testid="signal-same-situation-gone">
              {$_('insights.signal.same_situation_gone')}
            </p>
          {:else if sameSituation.effectSurvives === true}
            <p class="signal-page__hint" data-testid="signal-same-situation-stays">
              {$_('insights.signal.same_situation_stays')}
            </p>
          {/if}
        {/if}
      </section>
    {/if}

    <section class="signal-page__card">
      <div class="signal-page__row">
        <h2>{$_('insights.signal.course_heading')}</h2>
        {#if canOpenEsm}
          <button
            type="button"
            class="signal-page__chip"
            data-testid="signal-open-esm"
            on:click={() => void openEsm()}
          >
            {$_('trends.esm.open_action')}
          </button>
        {/if}
      </div>
      {#if verification && verification.with_mean != null && verification.without_mean != null}
        <p class="signal-page__means" data-testid="signal-means">
          {$_('insights.signal.means', {
            values: {
              withMean: verification.with_mean.toFixed(1),
              withoutMean: verification.without_mean.toFixed(1),
              withN: verification.with_n,
              withoutN: verification.without_n,
            },
          })}
        </p>
      {/if}
      <div class="signal-page__actions">
        <button
          type="button"
          class="signal-page__chip"
          data-testid="signal-toggle-scatter"
          aria-expanded={showScatter}
          on:click={() => (showScatter = !showScatter)}
        >
          {showScatter ? $_('insights.signal.scatter_hide') : $_('insights.signal.scatter_show')}
        </button>
        <a class="signal-page__chip" href="/trends" data-testid="signal-pin-trends">
          {$_('insights.signal.pin_trends')}
        </a>
        <a class="signal-page__chip" href="/insights/report" data-testid="signal-report-link">
          {$_('insights.signal.remember_report')}
        </a>
      </div>
      {#if showScatter && verification}
        <SignalScatter
          points={verification.points}
          withMean={verification.with_mean}
          withoutMean={verification.without_mean}
          withSe={verification.with_se}
          withoutSe={verification.without_se}
          subjectLabel={insight.subject_label ?? ''}
          showUncertainty={showUncertaintyRibbon}
        />
        <p class="signal-page__privacy">{$_('insights.signal.scatter_privacy')}</p>
      {/if}
    </section>

    {#if isNull}
      <section class="signal-page__card signal-page__card--next" data-testid="signal-next-actions">
        <h2>{$_('insights.signal.next_heading')}</h2>
        <p>{$_('insights.signal.next_body')}</p>
        <div class="signal-page__actions">
          <a href="/entries/new" class="signal-page__chip">{$_('insights.signal.next_log')}</a>
          <a href="/trends" class="signal-page__chip">{$_('insights.signal.next_compare')}</a>
          <a href="/insights" class="signal-page__chip">{$_('insights.signal.next_other')}</a>
        </div>
      </section>
    {/if}
  {/if}
</main>

{#if esmOpen}
  <EventAlignedSmallMultiplesSheet
    open={esmOpen && !esmLoading}
    events={esmWindows}
    points={esmPoints}
    metric={insight ? insightMetricToChartKey(insight.metric) : 'mood_avg'}
    lagOffset={esmLag}
    phase={maturity?.phase ?? null}
    on:close={() => {
      esmOpen = false;
    }}
  />
{/if}

<style>
  .signal-page__status {
    color: var(--color-text-muted);
  }
  .signal-page__card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3, 0.75rem);
    padding: var(--space-4, 1rem);
    background: var(--color-surface);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    border-radius: var(--radius-lg, 0.75rem);
  }
  .signal-page__card--next {
    border-left: 3px solid var(--color-success, #2f6f4e);
  }
  .signal-page__statement {
    margin: 0;
    font-size: var(--text-md, 1rem);
    line-height: 1.45;
  }
  .signal-page__hint,
  .signal-page__means,
  .signal-page__privacy {
    margin: 0;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
  .signal-page__row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }
  .signal-page__row h2,
  .signal-page__card h2 {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 600;
  }
  .signal-page__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .signal-page__chip {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.65rem;
    border-radius: var(--radius-full, 999px);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--text-xs, 0.75rem);
    text-decoration: none;
    cursor: pointer;
  }
</style>
