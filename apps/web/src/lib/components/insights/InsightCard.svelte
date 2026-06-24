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
   * retry        Dispatched when the user clicks the error-state retry button
   * dismiss      Dispatched when the user clicks the dismiss button
   * exportCsv    Dispatched when the user clicks "Export CSV" (stub, #169)
   * exploreEvents Dispatched from an explicitly enabled, parent-wired affordance
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import InsightConfidenceScale from './InsightConfidenceScale.svelte';
  import InsightMaturityBadge from './InsightMaturityBadge.svelte';
  import { isSmallMultiplesUnlocked } from '$lib/components/trends/smallMultiplesGate';
  import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse | null = null;
  export let maturity: InsightMaturity | null = null;
  export let loading = false;
  export let error = '';
  export let inactiveTagIds: readonly string[] = [];
  export let enableExploreEvents = false;
  export let featured = false;
  export let showConfidenceSummary = false;

  const dispatch = createEventDispatcher<{
    retry: void;
    dismiss: { id: string };
    exportCsv: { id: string };
    exploreEvents: { id: string };
  }>();

  // Sprint 3 (ADR-0035 §6): only surface the action when a parent has wired
  // the sheet and the insight has reached the provisional phase.
  $: canExploreEvents = enableExploreEvents && isSmallMultiplesUnlocked(maturity?.phase ?? null);

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
    const a = ins.metric ?? '?';
    const b = ins.subject_label ?? null;
    return b ? `${a} → ${b}` : a;
  }

  const SVG_W = 280;
  const SVG_H = 72;
  const PAD = 10;

  function sparkPoints(baseline: number, r: number, n: number): string {
    const pts: [number, number][] = [];
    const steps = Math.min(n, 12);
    for (let i = 0; i < steps; i++) {
      const t = i / Math.max(steps - 1, 1);
      const x = PAD + t * (SVG_W - PAD * 2);
      const noise = Math.sin(i * 2.1 + baseline * 10) * 0.18;
      const y_norm = Math.min(1, Math.max(0, baseline + noise + r * t * 0.25));
      const y = PAD + (1 - y_norm) * (SVG_H - PAD * 2);
      pts.push([x, y]);
    }
    return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  }

  $: title = insight ? buildTitle(insight) : '';
  $: glyph = insight ? directionGlyph(insight.effect_size ?? 0) : '→';
  $: dirClass = insight ? directionClass(insight.effect_size ?? 0) : 'neutral';
  $: seriesA = insight ? sparkPoints(0.6, insight.effect_size ?? 0, insight.sample_n ?? 10) : '';
  $: seriesB = insight
    ? sparkPoints(0.45, -(insight.effect_size ?? 0) * 0.6, insight.sample_n ?? 10)
    : '';
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
    data-testid="insight-card"
    data-expanded={expanded ? 'true' : 'false'}
    data-direction={dirClass}
    data-featured={featured ? 'true' : 'false'}
  >
    <header class="insight-card__header">
      <span
        class="insight-card__direction insight-card__direction--{dirClass}"
        aria-hidden="true"
        data-testid="insight-card-direction">{glyph}</span
      >
      <h3 class="insight-card__title" data-testid="insight-card-title">
        {title}
        {#if isInactiveTag}
          <span class="insight-card__inactive-badge">{$_('insights.card.inactive_tag_badge')}</span>
        {/if}
      </h3>
      <button
        class="insight-card__dismiss"
        aria-label={$_('insights.card.dismiss_aria', { values: { title } })}
        data-testid="insight-card-dismiss"
        on:click={() => dispatch('dismiss', { id: insight.id })}
      >
        ✕
      </button>
    </header>

    {#if maturity}
      <InsightMaturityBadge {maturity} entryCount={insight.sample_n ?? 0} />
    {/if}

    <p class="insight-card__statement" data-testid="insight-card-statement">
      {insight.statement ?? $_('home.insight.empty_statement')}
    </p>

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
    </p>

    {#if showConfidenceSummary && !expanded}
      <div class="insight-card__confidence-summary" data-testid="insight-card-confidence-summary">
        <InsightConfidenceScale
          confidenceScore={insight.confidence ?? 0}
          currentTier={insight.tier}
          entryCount={insight.sample_n ?? 0}
        />
      </div>
    {/if}

    <a
      href="/insights/disclaimer"
      class="insight-card__disclaimer"
      data-testid="insight-card-disclaimer"
      rel="noopener"
    >
      {$_('insights.card.disclaimer_link')} <span aria-hidden="true">ⓘ</span>
    </a>

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
        <InsightConfidenceScale
          confidenceScore={insight.confidence ?? 0}
          currentTier={insight.tier}
          entryCount={insight.sample_n ?? 0}
          loading={false}
          showRawPercent
        />

        <div
          class="insight-card__chart"
          data-testid="insight-card-chart"
          role="img"
          aria-label={$_('insights.card.chart_aria', { values: { title } })}
        >
          <svg
            viewBox="0 0 {SVG_W} {SVG_H}"
            width={SVG_W}
            height={SVG_H}
            aria-hidden="true"
            class="insight-card__sparkline"
          >
            {#each [0.25, 0.5, 0.75] as frac}
              <line
                x1={PAD}
                y1={PAD + (1 - frac) * (SVG_H - PAD * 2)}
                x2={SVG_W - PAD}
                y2={PAD + (1 - frac) * (SVG_H - PAD * 2)}
                stroke="var(--color-divider)"
                stroke-width="0.5"
              />
            {/each}
            <polyline
              points={seriesA}
              fill="none"
              stroke="var(--color-primary)"
              stroke-width="1.5"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <polyline
              points={seriesB}
              fill="none"
              stroke="var(--color-orange)"
              stroke-width="1.5"
              stroke-linejoin="round"
              stroke-linecap="round"
              stroke-dasharray="4 2"
            />
          </svg>
          <div class="insight-card__chart-legend">
            <span class="insight-card__legend-dot insight-card__legend-dot--primary"></span>
            <span class="insight-card__legend-label">{insight.metric}</span>
            {#if insight.subject_label}
              <span class="insight-card__legend-dot insight-card__legend-dot--secondary"></span>
              <span class="insight-card__legend-label">{insight.subject_label}</span>
            {/if}
          </div>
        </div>

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

        <button
          class="insight-card__export-btn"
          data-testid="insight-card-export-csv"
          on:click={() => dispatch('exportCsv', { id: insight.id })}
        >
          {$_('insights.card.export_csv')}
        </button>
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
    border-radius: var(--radius-lg, 0.75rem);
    box-shadow: var(--shadow-sm);
    transition: box-shadow 200ms ease;
  }
  .insight-card--featured {
    border-color: color-mix(in srgb, var(--color-primary) 42%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 4%, var(--color-surface));
  }
  .insight-card__header {
    display: flex;
    align-items: center;
    gap: var(--space-2, 0.5rem);
  }
  .insight-card__direction {
    font-size: 1.1rem;
    font-weight: 700;
    width: 1.5rem;
    text-align: center;
    flex-shrink: 0;
  }
  .insight-card__direction--positive {
    color: var(--color-success);
  }
  .insight-card__direction--negative {
    color: var(--color-notification);
  }
  .insight-card__direction--neutral {
    color: var(--color-text-muted);
  }
  .insight-card__title {
    flex: 1;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 600;
    margin: 0;
    line-height: 1.3;
  }
  .insight-card__inactive-badge {
    display: inline-flex;
    margin-left: var(--space-2, 0.5rem);
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    border: 1px solid var(--color-border);
    color: var(--color-text-muted);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 500;
    white-space: nowrap;
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
    font-size: 0.75rem;
    line-height: 1;
    transition:
      color var(--transition-interactive, 180ms ease),
      background var(--transition-interactive, 180ms ease);
  }
  .insight-card__dismiss:hover,
  .insight-card__dismiss:focus-visible {
    color: var(--color-text);
    background: var(--color-surface-offset);
  }
  .insight-card__statement {
    font-size: var(--text-sm, 0.875rem);
    line-height: 1.55;
    color: var(--color-text);
    margin: 0;
  }
  .insight-card__meta {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    margin: 0;
  }
  .insight-card__inactive-hint::before {
    content: ' · ';
  }
  .insight-card__disclaimer {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    text-decoration: underline;
    text-decoration-style: dotted;
    text-underline-offset: 2px;
    align-self: flex-start;
  }
  .insight-card__disclaimer:hover {
    color: var(--color-primary);
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
    transition: color var(--transition-interactive, 180ms ease);
  }
  .insight-card__toggle:hover {
    color: var(--color-primary-hover);
  }
  .insight-card__toggle-icon {
    font-size: 0.6rem;
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
    animation: fadeSlideIn 180ms ease both;
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
  .insight-card__chart {
    display: flex;
    flex-direction: column;
    gap: var(--space-2, 0.5rem);
    background: var(--color-surface-2);
    border-radius: var(--radius-md, 0.5rem);
    padding: var(--space-3, 0.75rem);
  }
  .insight-card__sparkline {
    width: 100%;
    height: auto;
    display: block;
  }
  .insight-card__chart-legend {
    display: flex;
    align-items: center;
    gap: var(--space-2, 0.5rem);
  }
  .insight-card__legend-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .insight-card__legend-dot--primary {
    background: var(--color-primary);
  }
  .insight-card__legend-dot--secondary {
    background: var(--color-orange);
  }
  .insight-card__legend-label {
    font-size: var(--text-xs, 0.72rem);
    color: var(--color-text-muted);
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
  .insight-card__export-btn {
    align-self: flex-start;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    border: 1px solid oklch(from var(--color-text) l c h / 0.15);
    border-radius: var(--radius-sm, 0.375rem);
    padding: var(--space-1, 0.25rem) var(--space-3, 0.75rem);
    transition:
      color var(--transition-interactive, 180ms ease),
      border-color var(--transition-interactive, 180ms ease);
  }
  .insight-card__export-btn:hover {
    color: var(--color-text);
    border-color: oklch(from var(--color-text) l c h / 0.3);
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
    transition: background var(--transition-interactive, 180ms ease);
  }
  .insight-card__explore:hover,
  .insight-card__explore:focus-visible {
    background: var(--color-surface-muted, var(--color-strip-track-bg));
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
    border-radius: 999px;
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
    transition: background var(--transition-interactive, 180ms ease);
  }
  .insight-card__retry-btn:hover {
    background: oklch(from var(--color-primary) l c h / 0.08);
  }
  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
      opacity: 0.6;
    }
    .insight-card__level2 {
      animation: none;
    }
  }
</style>
