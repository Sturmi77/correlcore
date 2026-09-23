<script lang="ts">
  /**
   * /insights/signal/[id] — Ebene 2 verification surface (Phase 7 / ADR-0043).
   * Sentence → with/without (G2) → course/ESM → scatter (G1) behind disclosure.
   */
  import { ApiError } from '$lib/api/client';
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
  import { fetchSymptomHeatmap, fetchTagHeatmap } from '$lib/api/stats';
  import { listEntries } from '$lib/api/entries';
  import {
    insightMetricToChartKey,
    insightMetricToEntryField,
    isExploreEventsSubject,
  } from '$lib/utils/exploreEventWindows';
  import { isNullAssociation, parseWithWithoutView } from '$lib/utils/withWithoutDistribution';
  import { parseSameSituationView } from '$lib/utils/sameSituation';
  import { stripLegacyInsightStatementTails } from '$lib/utils/stripLegacyInsightStatementTails';
  import { isLagInsight, isSameDaySleepSpearman } from '$lib/utils/lagInsight';
  import SignalLagEvidence from '$lib/components/insights/SignalLagEvidence.svelte';
  import {
    isSmallMultiplesUnlocked,
    SMALL_MULTIPLES_RADIUS,
  } from '$lib/components/trends/smallMultiplesGate';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';
  import {
    analysisPairQuery,
    insightMatchesAnalysisPair,
    parseAnalysisPair,
    partnerForInsight,
  } from '$lib/utils/analysisPairHandoff';
  import { presenceDatesForPartner, type EsmPartner } from '$lib/utils/esmPartner';
  import { buildWorkContextHeatmap } from '$lib/utils/workContextHeatmap';
  import { shiftIsoDate } from '$lib/utils/isoDate';

  let insight: InsightResponse | null = null;
  let maturity: InsightMaturity | null = null;
  let verification: InsightVerificationResponse | null = null;
  /** True when this subject cannot carry a day-level series (composite, metric). */
  let verificationUnsupported = false;

  /** Raw enum values (`office`, `travel`) have translated labels — use them (#967). */
  function workContextLabel(value: string | null): string {
    if (!value) return '';
    const key = `entry.work_context.${value}`;
    const label = $_(key);
    return label === key ? value : label;
  }
  let loading = true;
  let error: string | null = null;
  let showScatter = false;
  let showSameSituation = false;
  let esmOpen = false;
  let esmWindows: EventWindow[] = [];
  let esmPoints: TimeseriesPoint[] = [];
  let esmLag: number | null = null;
  let esmLoading = false;
  let esmPartnerLoading = false;
  let esmPartner: EsmPartner | null = null;
  let esmPartnerPresence: string[] = [];
  let esmPartnerUnavailable = false;
  let mounted = false;
  let activeContext = '';
  let requestGeneration = 0;
  let detailAbort: AbortController | null = null;
  let esmAbort: AbortController | null = null;

  $: insightId = $page.params.id ?? '';
  $: authenticatedUserId = $auth.status === 'authenticated' ? $auth.user.id : '';
  $: carriedPair = parseAnalysisPair($page.url.searchParams);
  $: carriedPairQuery = carriedPair ? analysisPairQuery(carriedPair) : '';
  $: requestedContext =
    authenticatedUserId && insightId ? `${authenticatedUserId}:${insightId}` : '';
  $: if (mounted && requestedContext && requestedContext !== activeContext) {
    activeContext = requestedContext;
    void load(insightId, authenticatedUserId);
  }
  $: if (mounted && $auth.status === 'anonymous') {
    const next = `${$page.url.pathname}${$page.url.search}`;
    void goto(`/auth/login?next=${encodeURIComponent(next)}`);
  }
  $: withWithout = insight ? parseWithWithoutView(insight) : null;
  $: sameSituation = insight ? parseSameSituationView(insight) : null;
  $: isNull = insight ? isNullAssociation(insight) : false;
  $: isLag = insight ? isLagInsight(insight) : false;
  $: isSameDaySleep = insight ? isSameDaySleepSpearman(insight) : false;
  $: title =
    insight?.subject_label && insight.metric
      ? `${insight.subject_label} → ${insight.metric}`
      : $_('insights.signal.title_fallback');
  $: canOpenEsm =
    Boolean(insight && isExploreEventsSubject(insight)) &&
    isSmallMultiplesUnlocked(maturity?.phase ?? null);
  $: showUncertaintyRibbon = maturity?.phase !== 'robust';

  async function load(requestedId: string, actorId: string): Promise<void> {
    if (!requestedId || !actorId) return;
    const generation = ++requestGeneration;
    detailAbort?.abort();
    esmAbort?.abort();
    const controller = new AbortController();
    detailAbort = controller;
    loading = true;
    error = null;
    insight = null;
    verification = null;
    verificationUnsupported = false;
    maturity = null;
    esmOpen = false;
    esmLoading = false;
    esmPartner = null;
    esmPartnerPresence = [];
    esmPartnerUnavailable = false;
    try {
      const [detail, latest] = await Promise.all([
        fetchInsight(requestedId, { signal: controller.signal }),
        listLatestInsights({ limit: 1 }).catch(() => null),
      ]);
      if (
        generation !== requestGeneration ||
        requestedId !== insightId ||
        actorId !== authenticatedUserId
      ) {
        return;
      }
      insight = detail;
      maturity = latest?.insight_maturity ?? null;
      // Composite subjects (the Belastung overlay's own insight) have no
      // day-level presence series, so the endpoint answers 422. Swallowing that
      // left the section blank and made both Belastung CTAs look broken (#967).
      verificationUnsupported = false;
      let nextVerificationUnsupported = false;
      const nextVerification = await fetchInsightVerification(requestedId, '90d', {
        signal: controller.signal,
      }).catch((err) => {
        if (err instanceof ApiError && err.status === 422) nextVerificationUnsupported = true;
        return null;
      });
      if (
        generation !== requestGeneration ||
        requestedId !== insightId ||
        actorId !== authenticatedUserId
      ) {
        return;
      }
      verificationUnsupported = nextVerificationUnsupported;
      verification = nextVerification;
    } catch (err) {
      if (controller.signal.aborted || generation !== requestGeneration) return;
      error = err instanceof Error ? err.message : $_('insights.signal.error');
      insight = null;
      verification = null;
    } finally {
      if (generation === requestGeneration) loading = false;
    }
  }

  async function openEsm(): Promise<void> {
    if (!insight) return;
    const requestedId = insight.id;
    const generation = requestGeneration;
    esmAbort?.abort();
    const controller = new AbortController();
    esmAbort = controller;
    esmOpen = true;
    esmLoading = true;
    esmPartnerLoading = false;
    esmPartner = null;
    esmPartnerPresence = [];
    esmPartnerUnavailable = false;
    try {
      const response = await fetchInsightEventWindows(requestedId, '90d', {
        signal: controller.signal,
      });
      if (
        controller.signal.aborted ||
        generation !== requestGeneration ||
        insight?.id !== requestedId
      ) {
        return;
      }
      esmWindows = response.events.map((event) => ({
        onset: event.onset,
        label: event.label ?? undefined,
      }));
      esmPoints = response.points;
      esmLag = response.lag_days ?? null;
      // The primary visualization is complete. Open it while optional partner
      // presence loads and let the sheet render its dedicated loading state.
      esmLoading = false;

      const partnerRef =
        carriedPair && insightMatchesAnalysisPair(insight, carriedPair)
          ? partnerForInsight(insight, carriedPair)
          : null;
      if (partnerRef && ['tag', 'symptom', 'work_context'].includes(partnerRef.kind)) {
        esmPartnerLoading = true;
        const partner: EsmPartner = {
          id: partnerRef.id,
          label: partnerRef.label ?? partnerRef.context ?? partnerRef.id,
          kind: partnerRef.kind as EsmPartner['kind'],
        };
        const startDate = shiftIsoDate(response.start_date, -SMALL_MULTIPLES_RADIUS);
        const endDate = shiftIsoDate(response.end_date, SMALL_MULTIPLES_RADIUS);
        try {
          let partnerPresence: string[];
          if (partner.kind === 'tag') {
            const heatmap = await fetchTagHeatmap({ start_date: startDate, end_date: endDate });
            partnerPresence = presenceDatesForPartner(partner, heatmap, null);
          } else if (partner.kind === 'symptom') {
            const heatmap = await fetchSymptomHeatmap({ start_date: startDate, end_date: endDate });
            partnerPresence = presenceDatesForPartner(partner, null, heatmap);
          } else {
            const entries = await listEntries({
              start_date: startDate,
              end_date: endDate,
              limit: 500,
            });
            partnerPresence = presenceDatesForPartner(
              partner,
              null,
              null,
              buildWorkContextHeatmap(entries, {
                start_date: startDate,
                end_date: endDate,
              })
            );
          }
          if (
            controller.signal.aborted ||
            generation !== requestGeneration ||
            insight?.id !== requestedId
          ) {
            return;
          }
          esmPartner = partner;
          esmPartnerPresence = partnerPresence;
        } catch {
          if (controller.signal.aborted || generation !== requestGeneration) return;
          esmPartnerUnavailable = true;
        } finally {
          if (!controller.signal.aborted && generation === requestGeneration) {
            esmPartnerLoading = false;
          }
        }
      }
    } catch {
      if (controller.signal.aborted || generation !== requestGeneration) return;
      esmWindows = [];
      esmPoints = [];
      esmLag = null;
      esmPartner = null;
      esmPartnerPresence = [];
      esmPartnerLoading = false;
    } finally {
      if (!controller.signal.aborted && generation === requestGeneration) esmLoading = false;
    }
  }

  onMount(() => {
    mounted = true;
    const unregisterRefresh = registerPageRefresh(() => {
      if (authenticatedUserId && insightId) void load(insightId, authenticatedUserId);
    });
    return () => {
      mounted = false;
      requestGeneration += 1;
      detailAbort?.abort();
      esmAbort?.abort();
      unregisterRefresh();
    };
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
    back={{
      href: `/insights${carriedPairQuery ? `?${carriedPairQuery}` : ''}`,
      label: $_('insights.signal.back'),
    }}
  />

  {#if loading}
    <p class="signal-page__status">{$_('insights.signal.loading')}</p>
  {:else if error}
    <InlineAlert variant="error" message={error} />
  {:else if insight}
    <section class="signal-page__card" data-testid="signal-statement">
      <p class="signal-page__statement">
        {stripLegacyInsightStatementTails(insight.statement) || $_('home.insight.empty_statement')}
      </p>
      {#if isLag}
        <p class="signal-page__badge" data-testid="signal-zeitversatz-badge">
          {$_('insights.signal.zeitversatz_badge')}
        </p>
      {:else if isSameDaySleep}
        <p class="signal-page__badge" data-testid="signal-same-day-badge">
          {$_('insights.signal.same_day_badge')}
        </p>
      {/if}
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

    {#if isLag}
      <section class="signal-page__card">
        <SignalLagEvidence {insight} />
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
                context: workContextLabel(sameSituation.context),
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
      {#if verificationUnsupported}
        <InlineAlert
          variant="info"
          message={$_('insights.signal.verification_unsupported')}
          testId="signal-verification-unsupported"
        />
      {/if}
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
        <a
          class="signal-page__chip"
          href={`/insights/report?signal=${encodeURIComponent(insight.id)}${carriedPairQuery ? `&${carriedPairQuery}` : ''}`}
          data-testid="signal-report-link"
        >
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
          metric={insightMetricToEntryField(insight.metric)}
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
    partner={esmPartner}
    partnerPresenceDates={esmPartnerPresence}
    partnerCandidates={esmPartner ? [{ ...esmPartner, score: Number.MAX_SAFE_INTEGER }] : []}
    partnerLoading={esmPartnerLoading}
    partnerUnavailable={esmPartnerUnavailable}
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
  .signal-page__badge {
    margin: 0;
    align-self: flex-start;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm, 0.35rem);
    background: oklch(from var(--color-primary) l c h / 0.12);
    color: var(--color-text);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
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
