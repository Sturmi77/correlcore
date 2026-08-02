<script lang="ts">
  /**
   * InsightCard — ADR-0017, ADR-0018, FRONTEND.md §6.1 / §6.2
   *
   * Three-level progressive disclosure for a single Insight.
   *
   * Props
   * -----
   * insight      InsightResponse from $lib/api/insights (required)
   * loading      Show shimmer skeleton instead of real content
   * error        Non-empty string renders the error state with a retry button
   *
   * Events
   * ------
   * retry         Dispatched when the user clicks the error-state retry button
   * dismiss       Dispatched when the user clicks the dismiss button (parent must wire)
   * exploreEvents Dispatched from an explicitly enabled, parent-wired affordance
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import {
    isCalendarContextConfounded,
    isCalendarContextInsight,
    primaryInsightConfounder,
    type InsightConfounder,
  } from '$lib/utils/insightConfounder';
  import InsightEvidence from './InsightEvidence.svelte';
  import NoteInsightEvidence from './NoteInsightEvidence.svelte';
  import { isSmallMultiplesUnlocked } from '$lib/components/trends/smallMultiplesGate';
  import { isExploreEventsSubject } from '$lib/utils/exploreEventWindows';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse | null = null;
  export let maturity: InsightMaturity | null = null;
  export let loading = false;
  export let error = '';
  export let inactiveTagIds: readonly string[] = [];
  export let enableExploreEvents = false;
  export let featured = false;
  export let showConfidenceSummary = false;
  /** Hide per-card phase badge when page-level maturity chrome is shown (O-01). */
  export let showMaturityBadge = true;
  /** When false, hide the dismiss control (e.g. digest preview cards). */
  export let dismissable = true;

  const dispatch = createEventDispatcher<{
    retry: void;
    dismiss: { id: string };
    exploreEvents: { id: string };
    selectDate: { date: string };
  }>();

  // Sprint 3 (ADR-0035 §6): only surface the action when a parent has wired
  // the sheet and the insight has reached the provisional phase.
  $: canExploreEvents =
    enableExploreEvents &&
    isSmallMultiplesUnlocked(maturity?.phase ?? null) &&
    Boolean(insight && isExploreEventsSubject(insight));

  function payloadRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
  }

  $: noteEvidence = payloadRecord(insight?.payload?.evidence);
  $: hasNoteEvidence = Boolean(
    noteEvidence &&
    (typeof noteEvidence.marker === 'string' || typeof noteEvidence.signal === 'string')
  );

  let expanded = false;

  function toggleExpanded() {
    expanded = !expanded;
  }

  function directionGlyph(effectSize: number): string {
    if (effectSize > 0.05) return '↗';
    if (effectSize < -0.05) return '↘';
    return '→';
  }

  function directionClass(effectSize: number): string {
    if (effectSize > 0.05) return 'positive';
    if (effectSize < -0.05) return 'negative';
    return 'neutral';
  }

  function payloadString(ins: InsightResponse, key: string): string | null {
    const value = ins.payload?.[key];
    return typeof value === 'string' && value.length > 0 ? value : null;
  }

  function payloadNumber(ins: InsightResponse, key: string): number | null {
    const value = ins.payload?.[key];
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  }

  // #488 Phase 1b: a small lag profile (r at each day 1..7) for lag insights,
  // rendered only when the payload carries the series. Non-causal — magnitude
  // bars with the chosen lag highlighted; missing lags render as a baseline.
  const LAG_PROFILE_MAX_DAYS = 7;

  type LagProfileBar = { lag: number; r: number; active: boolean };

  function lagProfileBars(ins: InsightResponse): LagProfileBar[] | null {
    const payload = ins.payload as Record<string, unknown> | undefined;
    if (!payload || payload.method !== 'lag') return null;
    const raw = payload.lag_profile;
    if (!Array.isArray(raw) || raw.length < 2) return null;
    const chosen = payloadNumber(ins, 'lag_days');
    const byLag = new Map<number, number>();
    for (const point of raw) {
      if (
        point &&
        typeof point === 'object' &&
        typeof (point as { lag?: unknown }).lag === 'number' &&
        typeof (point as { r?: unknown }).r === 'number'
      ) {
        byLag.set((point as { lag: number }).lag, (point as { r: number }).r);
      }
    }
    if (byLag.size < 2) return null;
    const bars: LagProfileBar[] = [];
    for (let lag = 1; lag <= LAG_PROFILE_MAX_DAYS; lag += 1) {
      bars.push({ lag, r: byLag.get(lag) ?? 0, active: lag === chosen });
    }
    return bars;
  }

  $: lagProfile = insight ? lagProfileBars(insight) : null;
  $: lagProfileMaxAbs = lagProfile
    ? Math.max(...lagProfile.map((bar) => Math.abs(bar.r)), 0.0001)
    : 1;

  function lagBarHeight(r: number): number {
    // Floor non-zero bars so a real-but-small correlation stays visible.
    const ratio = Math.abs(r) / lagProfileMaxAbs;
    return r === 0 ? 0 : Math.max(8, Math.round(ratio * 100));
  }

  function workContextLabel(ins: InsightResponse): string | null {
    const explicit = payloadString(ins, 'work_context_label');
    if (explicit) return explicit;
    const context = payloadString(ins, 'work_context');
    if (!context) return null;
    const translated = $_(`entry.work_context.${context}`);
    return translated === `entry.work_context.${context}` ? context : translated;
  }

  function weekdayLabel(ins: InsightResponse): string | null {
    const explicit =
      payloadString(ins, 'weekday_label') ??
      payloadString(ins, 'weekday_name') ??
      payloadString(ins, 'weekday');
    if (explicit) return explicit;
    const weekday = payloadNumber(ins, 'weekday');
    const keys = [
      'home.weekday.mon',
      'home.weekday.tue',
      'home.weekday.wed',
      'home.weekday.thu',
      'home.weekday.fri',
      'home.weekday.sat',
      'home.weekday.sun',
    ];
    return weekday === null ? null : $_(keys[weekday] ?? 'home.weekday.mon');
  }

  function metricLabel(metric: string | null | undefined): string {
    if (metric === 'mood' || metric === 'mood_score' || !metric) return $_('trends.metric.mood');
    if (metric === 'energy' || metric === 'energy_avg') return $_('trends.metric.energy');
    if (metric === 'stress' || metric === 'stress_avg') return $_('trends.metric.stress');
    return metric;
  }

  /**
   * Sprint 3 (ISP-5): accent the card by which metric the insight is about,
   * reusing tokens that previously only fed chart lines (lib/utils/charts.ts).
   * Falls back to the generic primary for non-core-metric insights (tags,
   * symptoms, context patterns) rather than guessing a color for them.
   */
  function metricAccentVar(metric: string | null | undefined): string {
    if (metric === 'mood' || metric === 'mood_score') return 'var(--color-metric-mood)';
    if (metric === 'energy' || metric === 'energy_avg') return 'var(--color-metric-energy)';
    if (metric === 'stress' || metric === 'stress_avg') return 'var(--color-metric-stress)';
    return 'var(--color-primary)';
  }

  function payloadFeatureLabel(value: unknown): string | null {
    if (typeof value === 'string' && value.length > 0) return value;
    if (value && typeof value === 'object') {
      const record = value as Record<string, unknown>;
      if (typeof record.name === 'string' && record.name.length > 0) return record.name;
      if (typeof record.label === 'string' && record.label.length > 0) return record.label;
      if (typeof record.key === 'string' && record.key.length > 0) return record.key;
    }
    return null;
  }

  function buildTitle(ins: InsightResponse): string {
    if (ins.insight_type === 'symptom_mood_association') {
      const symptom = payloadString(ins, 'symptom_name') ?? ins.subject_label ?? 'Symptoms';
      return `${symptom} → ${ins.metric}`;
    }
    if (ins.insight_type === 'symptom_tag_cooccurrence') {
      const symptom = payloadString(ins, 'symptom_name') ?? 'Symptoms';
      const tag = payloadString(ins, 'tag_name') ?? ins.subject_label ?? 'Insight';
      return `${symptom} + ${tag}`;
    }
    if (ins.insight_type === 'work_context_pattern') {
      const context = workContextLabel(ins) ?? ins.subject_label ?? $_('insights.context.fallback');
      return `${metricLabel(ins.metric)} -> ${context}`;
    }
    if (ins.insight_type === 'weekday_context_pattern') {
      const weekday = weekdayLabel(ins) ?? ins.subject_label ?? $_('insights.context.weekday');
      const context = workContextLabel(ins) ?? $_('insights.context.work_context');
      return `${metricLabel(ins.metric)} -> ${weekday} + ${context}`;
    }
    if (ins.insight_type === 'symptom_cluster') {
      const method = payloadString(ins, 'method');
      const target =
        payloadFeatureLabel(ins.payload?.target) ?? metricLabel(ins.metric) ?? ins.metric;
      if (method === 'lasso') {
        const features = ins.payload?.features;
        const labels = Array.isArray(features)
          ? features
              .map((feature) => payloadFeatureLabel(feature))
              .filter((label): label is string => Boolean(label))
          : [];
        const featureText =
          labels.length > 0 ? labels.slice(0, 3).join(', ') : $_('insights.card.cluster_features');
        return `${featureText} → ${target}`;
      }
      if (method === 'lag') {
        const feature = payloadFeatureLabel(ins.payload?.feature) ?? ins.subject_label ?? 'Feature';
        const lagDays = payloadNumber(ins, 'lag_days');
        const lagSuffix =
          lagDays !== null ? ` (+${lagDays} ${$_('insights.card.lag_days_unit')})` : '';
        return `${feature} → ${target}${lagSuffix}`;
      }
    }
    const a = ins.metric ?? '?';
    const b = ins.subject_label ?? null;
    return b ? `${a} → ${b}` : a;
  }

  function confounderNoteKey(confounder: InsightConfounder | null): string {
    if (confounder === 'work_context') return 'insights.work_context_confounded_note';
    if (confounder === 'calendar_context') return 'insights.calendar_context_confounded_note';
    return 'insights.weekday_confounded_note';
  }

  $: accentColor = insight ? metricAccentVar(insight.metric) : 'var(--color-primary)';
  $: isConfounded = insight ? isCalendarContextConfounded(insight) : false;
  $: primaryConfounder = insight ? primaryInsightConfounder(insight) : null;
  $: isContextInsight = insight ? isCalendarContextInsight(insight) : false;
  $: title = insight ? buildTitle(insight) : '';
  $: glyph = insight ? directionGlyph(insight.effect_size ?? 0) : '→';
  $: dirClass = insight ? directionClass(insight.effect_size ?? 0) : 'neutral';
  $: expandLabel = expanded ? $_('insights.card.collapse_aria') : $_('insights.card.expand_aria');
  $: isInactiveTag =
    insight?.subject_type === 'tag' &&
    typeof insight.subject_id === 'string' &&
    inactiveTagIds.includes(insight.subject_id);
</script>

{#if loading}
  <article
    class="insight-card insight-card--skeleton"
    aria-label={$_('insights.card.loading_aria')}
    aria-busy="true"
    data-testid="insight-card-skeleton"
  >
    <div class="skeleton skeleton-heading"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-text" style="width:70%"></div>
    <div class="skeleton skeleton-track" style="margin-top:0.5rem"></div>
  </article>
{:else if error}
  <article class="insight-card insight-card--error" data-testid="insight-card-error" role="alert">
    <p class="insight-card__error-msg">{$_('insights.card.error_body')}</p>
    <button
      class="insight-card__retry-btn"
      data-testid="insight-card-retry"
      on:click={() => dispatch('retry')}
    >
      {$_('insights.card.retry')}
    </button>
  </article>
{:else if insight}
  <article
    class="insight-card"
    class:insight-card--featured={featured}
    class:insight-card--confounded={isConfounded}
    data-testid="insight-card"
    data-expanded={expanded ? 'true' : 'false'}
    data-direction={dirClass}
    data-featured={featured ? 'true' : 'false'}
    style="--insight-accent: {accentColor}"
  >
    <header class="insight-card__header">
      <span
        class="insight-card__direction insight-card__direction--{dirClass}"
        aria-hidden="true"
        data-testid="insight-card-direction">{glyph}</span
      >
      <p class="insight-card__statement" data-testid="insight-card-statement">
        {insight.statement ?? $_('home.insight.empty_statement')}
      </p>
      {#if dismissable}
        <button
          class="insight-card__dismiss"
          aria-label={$_('insights.card.dismiss_aria', { values: { title } })}
          data-testid="insight-card-dismiss"
          on:click={() => dispatch('dismiss', { id: insight.id })}
        >
          ✕
        </button>
      {/if}
    </header>

    <p class="insight-card__caption" data-testid="insight-card-title">
      {title}
      {#if isContextInsight}
        <span class="insight-card__context-badge" data-testid="insight-card-context-badge">
          {$_('insights.context.badge')}
        </span>
      {/if}
      {#if isInactiveTag}
        <span class="insight-card__inactive-badge">{$_('insights.card.inactive_tag_badge')}</span>
      {/if}
    </p>

    {#if isConfounded}
      <p class="insight-card__confounder" data-testid="insight-card-confounder">
        {$_(confounderNoteKey(primaryConfounder))}
      </p>
    {/if}

    <p class="insight-card__meta" data-testid="insight-card-meta">
      {$_('insights.card.sample_meta', {
        values: {
          n: insight.sample_n ?? 0,
          days:
            typeof insight.payload?.time_window_days === 'number'
              ? insight.payload.time_window_days
              : 90,
        },
      })}
      {#if isInactiveTag}
        <span class="insight-card__inactive-hint">{$_('insights.card.inactive_tag_hint')}</span>
      {/if}
      <InsightEvidence
        {maturity}
        {showMaturityBadge}
        confidenceScore={insight.confidence ?? 0}
        currentTier={insight.tier}
        entryCount={insight.sample_n ?? 0}
        showConfidence={false}
      />
    </p>

    {#if showConfidenceSummary && !expanded}
      <div class="insight-card__confidence-summary" data-testid="insight-card-confidence-summary">
        <InsightEvidence
          confidenceScore={insight.confidence ?? 0}
          currentTier={insight.tier}
          entryCount={insight.sample_n ?? 0}
          showSample
        />
      </div>
    {/if}

    {#if hasNoteEvidence && noteEvidence}
      <NoteInsightEvidence
        marker={typeof noteEvidence.marker === 'string' ? noteEvidence.marker : null}
        signal={typeof noteEvidence.signal === 'string' ? noteEvidence.signal : null}
        sampleSize={typeof noteEvidence.sample_size === 'number'
          ? noteEvidence.sample_size
          : (insight?.sample_n ?? 0)}
        confidence={typeof noteEvidence.confidence === 'number'
          ? noteEvidence.confidence
          : (insight?.confidence ?? null)}
        avgDelta={typeof noteEvidence.avg_delta === 'number' ? noteEvidence.avg_delta : null}
        exampleDates={Array.isArray(insight?.payload?.example_dates)
          ? insight.payload.example_dates.filter((item): item is string => typeof item === 'string')
          : []}
        on:selectDate={(event) => dispatch('selectDate', event.detail)}
      />
    {/if}

    {#if lagProfile}
      <div class="insight-card__lag-profile" data-testid="insight-card-lag-profile">
        <span class="insight-card__lag-profile-label">
          {$_('insights.card.lag_profile_label')}
        </span>
        <div
          class="insight-card__lag-bars"
          role="img"
          aria-label={$_('insights.card.lag_profile_aria', {
            values: { days: payloadNumber(insight, 'lag_days') ?? 0 },
          })}
        >
          {#each lagProfile as bar (bar.lag)}
            <div class="insight-card__lag-col" class:insight-card__lag-col--active={bar.active}>
              <div class="insight-card__lag-bar-track">
                <div
                  class="insight-card__lag-bar"
                  style={`height: ${lagBarHeight(bar.r)}%; background: ${accentColor}`}
                  title={`+${bar.lag}d · r=${bar.r.toFixed(2)}`}
                ></div>
              </div>
              <span class="insight-card__lag-tick">{bar.lag}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#if canExploreEvents}
      <button
        type="button"
        class="insight-card__explore"
        data-testid="insight-card-explore-events"
        on:click={() => insight && dispatch('exploreEvents', { id: insight.id })}
      >
        {$_('trends.esm.open_action')}
      </button>
    {/if}

    <button
      class="insight-card__toggle"
      aria-expanded={expanded}
      aria-controls="insight-level2-{insight.id}"
      aria-label={expandLabel}
      data-testid="insight-card-toggle"
      on:click={toggleExpanded}
    >
      {expanded ? $_('insights.card.collapse') : $_('insights.card.expand')}
      <span aria-hidden="true" class="insight-card__toggle-icon">{expanded ? '▲' : '▼'}</span>
    </button>

    {#if expanded}
      <section
        id="insight-level2-{insight.id}"
        class="insight-card__level2"
        data-testid="insight-card-level2"
      >
        <InsightEvidence
          confidenceScore={insight.confidence ?? 0}
          currentTier={insight.tier}
          entryCount={insight.sample_n ?? 0}
          showSample
          detailed
          loading={false}
        />

        <dl class="insight-card__meta-grid" data-testid="insight-card-tech-meta">
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_confidence')}</dt>
            <dd data-testid="insight-card-confidence-raw">
              {((insight.confidence ?? 0) * 100).toFixed(0)}%
            </dd>
          </div>
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_effect')}</dt>
            <dd data-testid="insight-card-effect-size">
              {insight.effect_size != null ? insight.effect_size.toFixed(3) : '—'}
            </dd>
          </div>
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_type')}</dt>
            <dd>{insight.insight_type}</dd>
          </div>
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_sample')}</dt>
            <dd>{insight.sample_n}</dd>
          </div>
        </dl>
      </section>
    {/if}
  </article>
{/if}

<style>
  .insight-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3, 0.75rem);
    padding: var(--space-4, 1rem);
    background: var(--color-surface);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    border-left: 3px solid var(--insight-accent, var(--color-primary));
    border-radius: var(--radius-lg, 0.75rem);
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition-interactive);
  }
  .insight-card:hover,
  .insight-card:focus-within {
    box-shadow: var(--shadow-md);
  }
  .insight-card--featured {
    /* Longhand, not the border-color shorthand: keeps border-left's metric
       accent color from being clobbered on the featured card, where it's
       most visible. */
    border-top-color: color-mix(in srgb, var(--color-primary) 42%, var(--color-border));
    border-right-color: color-mix(in srgb, var(--color-primary) 42%, var(--color-border));
    border-bottom-color: color-mix(in srgb, var(--color-primary) 42%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 4%, var(--color-surface));
  }
  .insight-card--confounded {
    opacity: 0.88;
    border-style: dashed;
  }
  .insight-card__confounder {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }
  .insight-card__header {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2, 0.5rem);
  }
  .insight-card__direction {
    font-size: var(--text-lg);
    font-weight: 700;
    width: 1.5rem;
    text-align: center;
    flex-shrink: 0;
    line-height: 1.4;
  }
  .insight-card__direction--positive {
    color: var(--color-success);
  }
  .insight-card__direction--negative {
    color: var(--color-primary);
  }
  .insight-card__direction--neutral {
    color: var(--color-text-muted);
  }
  .insight-card__caption {
    font-size: var(--text-xs, 0.75rem);
    font-weight: 500;
    color: var(--color-text-faint);
    margin: 0;
    line-height: 1.3;
  }
  .insight-card__inactive-badge,
  .insight-card__context-badge {
    display: inline-flex;
    margin-left: var(--space-2, 0.5rem);
    padding: 0.1rem 0.4rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
    color: var(--color-text-muted);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 500;
    white-space: nowrap;
  }
  .insight-card__context-badge {
    background: color-mix(in srgb, var(--color-primary) 8%, var(--color-surface));
    color: var(--color-primary);
  }
  .insight-card__dismiss {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.75rem;
    min-height: 2.75rem;
    padding: 0;
    color: var(--color-text-muted);
    border-radius: var(--radius-sm, 0.375rem);
    font-size: var(--text-xs);
    line-height: 1;
    transition:
      color var(--transition-interactive),
      background var(--transition-interactive);
  }
  .insight-card__dismiss:hover,
  .insight-card__dismiss:focus-visible {
    color: var(--color-text);
    background: var(--color-surface-offset);
  }
  .insight-card__statement {
    flex: 1;
    font-size: var(--text-base, 1rem);
    font-weight: 550;
    line-height: 1.4;
    color: var(--color-fg);
    margin: 0;
  }
  .insight-card--featured .insight-card__statement {
    font-size: var(--text-xl, 1.5rem);
    /* Reveal once on mount; easing matches --transition-interactive's curve
       (that token is a duration+easing shorthand, not usable standalone here). */
    animation: insightStatementReveal var(--transition-sheet) both;
  }
  @keyframes insightStatementReveal {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .insight-card__meta {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    margin: 0;
    display: flex;
    align-items: center;
    gap: var(--space-2, 0.5rem);
    flex-wrap: wrap;
  }
  .insight-card__inactive-hint::before {
    content: ' · ';
  }
  /* #488 Phase 1b: lag profile mini-bars (days 1..7). Token-only colours. */
  .insight-card__lag-profile {
    display: flex;
    flex-direction: column;
    gap: var(--space-1, 0.25rem);
    margin-top: var(--space-1, 0.25rem);
  }
  .insight-card__lag-profile-label {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
  .insight-card__lag-bars {
    display: flex;
    align-items: flex-end;
    gap: var(--space-1, 0.25rem);
    height: 40px;
  }
  .insight-card__lag-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    flex: 1 1 0;
  }
  .insight-card__lag-bar-track {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    width: 100%;
    height: 28px;
  }
  .insight-card__lag-bar {
    width: 60%;
    min-height: 1px;
    border-radius: var(--radius-xs, 2px);
    opacity: 0.45;
  }
  .insight-card__lag-col--active .insight-card__lag-bar {
    opacity: 1;
  }
  .insight-card__lag-tick {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }
  .insight-card__lag-col--active .insight-card__lag-tick {
    color: var(--color-fg);
    font-weight: 600;
  }

  .insight-card__toggle {
    display: flex;
    align-items: center;
    gap: var(--space-1, 0.25rem);
    align-self: flex-start;
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    color: var(--color-primary);
    padding: var(--space-1, 0.25rem) 0;
    min-height: 2.75rem;
    border-radius: var(--radius-sm, 0.375rem);
    transition: color var(--transition-interactive);
  }
  .insight-card__toggle:hover {
    color: var(--color-primary-hover);
  }
  .insight-card__toggle-icon {
    font-size: var(--text-2xs);
  }
  .insight-card__confidence-summary {
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface-offset);
  }
  .insight-card__level2 {
    display: flex;
    flex-direction: column;
    gap: var(--space-4, 1rem);
    padding-top: var(--space-3, 0.75rem);
    border-top: 1px solid oklch(from var(--color-text) l c h / 0.08);
    animation: fadeSlideIn var(--transition-interactive) both;
  }
  @keyframes fadeSlideIn {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .insight-card__meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-1, 0.25rem) var(--space-4, 1rem);
  }
  .insight-card__meta-row {
    display: contents;
  }
  .insight-card__meta-grid dt {
    font-size: var(--text-xs, 0.72rem);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .insight-card__meta-grid dd {
    font-size: var(--text-xs, 0.72rem);
    font-weight: 600;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
    margin: 0;
  }
  /* Sprint 3 (ADR-0035 §6) — phase-gated explore-events affordance. */
  .insight-card__explore {
    align-self: flex-start;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 600;
    color: var(--color-fg);
    background: transparent;
    border: 1px solid var(--color-border, var(--color-border-chart));
    border-radius: var(--radius-sm, 0.375rem);
    padding: var(--space-1) var(--space-3);
    cursor: pointer;
    transition: background var(--transition-interactive);
  }
  .insight-card__explore:hover,
  .insight-card__explore:focus-visible {
    background: var(--color-strip-track-bg);
    outline: none;
  }
  .insight-card__explore:focus-visible {
    box-shadow: 0 0 0 2px var(--color-cursor-halo);
  }
  .insight-card--skeleton {
    pointer-events: none;
  }
  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }
  .skeleton {
    background: linear-gradient(
      90deg,
      var(--color-surface-offset) 25%,
      var(--color-surface-dynamic) 50%,
      var(--color-surface-offset) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: var(--radius-sm, 0.375rem);
  }
  .skeleton-heading {
    height: 1.1rem;
    width: 55%;
  }
  .skeleton-text {
    height: 0.85rem;
    width: 100%;
  }
  .skeleton-track {
    height: 0.55rem;
    width: 100%;
    border-radius: var(--radius-full);
  }
  .insight-card--error {
    border-color: oklch(from var(--color-error) l c h / 0.25);
    background: oklch(from var(--color-error) l c h / 0.04);
  }
  .insight-card__error-msg {
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-error);
    margin: 0;
  }
  .insight-card__retry-btn {
    align-self: flex-start;
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    color: var(--color-primary);
    padding: var(--space-1, 0.25rem) var(--space-3, 0.75rem);
    border: 1px solid var(--color-primary);
    border-radius: var(--radius-sm, 0.375rem);
    transition: background var(--transition-interactive);
  }
  .insight-card__retry-btn:hover {
    background: oklch(from var(--color-primary) l c h / 0.08);
  }
  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
      opacity: 0.6;
    }
    .insight-card__level2,
    .insight-card--featured .insight-card__statement {
      animation: none;
    }
  }
</style>
