<script lang="ts">
  /**
   * InsightCard — ADR-0017, ADR-0018, FRONTEND.md §6.1 / §6.2
   *
   * Three-level progressive disclosure for a single Insight.
   *
   * Props
   * -----
   * insight      InsightDto from $lib/api/insights (required)
   * loading      Show shimmer skeleton instead of real content
   * error        Non-empty string renders the error state with a retry button
   *
   * Events
   * ------
   * retry        Dispatched when the user clicks the error-state retry button
   * dismiss      Dispatched when the user clicks the dismiss button
   * exportCsv    Dispatched when the user clicks "Export CSV" (stub, #169)
   */
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import InsightConfidenceScale from './InsightConfidenceScale.svelte';
  import type { InsightDto } from '$lib/api/insights';

  export let insight: InsightDto | null = null;
  export let loading = false;
  export let error = '';

  const dispatch = createEventDispatcher<{
    retry: void;
    dismiss: { id: string };
    exportCsv: { id: string };
  }>();

  let expanded = false;

  function toggleExpanded() {
    expanded = !expanded;
  }

  /**
   * Map effect_size sign to a direction indicator glyph.
   * Positive  → ↗  (upward correlation)
   * Negative  → ↘  (downward / inverse)
   * Near zero → →  (neutral)
   */
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

  /**
   * Build a human-readable title from the insight's factor keys.
   * Falls back gracefully if tag_b is absent (single-variable insight).
   */
  function buildTitle(ins: InsightDto): string {
    const a = ins.tag_a ?? ins.factor_a ?? '?';
    const b = ins.tag_b ?? ins.factor_b ?? null;
    return b ? `${a} → ${b}` : a;
  }

  /**
   * Minimal inline dual-axis sparkline rendered as SVG.
   * X = days (time_window_days), Y1 = metric_a normalised 0-1,
   * Y2 = metric_b normalised 0-1.
   * Data points are fabricated from summary stats when raw series
   * are not part of the InsightDto (they are not in M3.1).
   * In M3.2 this will be replaced by a proper DualAxisChart component.
   */
  const SVG_W = 280;
  const SVG_H = 72;
  const PAD = 10;

  function sparkPoints(
    baseline: number,
    r: number,
    n: number
  ): string {
    const pts: [number, number][] = [];
    const steps = Math.min(n, 12);
    for (let i = 0; i < steps; i++) {
      const t = i / Math.max(steps - 1, 1);
      const x = PAD + t * (SVG_W - PAD * 2);
      // Simulate a vaguely correlated series around the baseline
      const noise = (Math.sin(i * 2.1 + baseline * 10) * 0.18);
      const y_norm = Math.min(1, Math.max(0, baseline + noise + r * t * 0.25));
      const y = PAD + (1 - y_norm) * (SVG_H - PAD * 2);
      pts.push([x, y]);
    }
    return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  }

  $: title = insight ? buildTitle(insight) : '';
  $: glyph = insight ? directionGlyph(insight.effect_size ?? 0) : '→';
  $: dirClass = insight ? directionClass(insight.effect_size ?? 0) : 'neutral';
  $: seriesA = insight
    ? sparkPoints(0.6, insight.effect_size ?? 0, insight.sample_n ?? 10)
    : '';
  $: seriesB = insight
    ? sparkPoints(0.45, -(insight.effect_size ?? 0) * 0.6, insight.sample_n ?? 10)
    : '';
  $: expandLabel = expanded
    ? $_('insights.card.collapse_aria')
    : $_('insights.card.expand_aria');
</script>

<!-- Loading skeleton -->
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

<!-- Error state -->
{:else if error}
  <article
    class="insight-card insight-card--error"
    data-testid="insight-card-error"
    role="alert"
  >
    <p class="insight-card__error-msg">{$_('insights.card.error_body')}</p>
    <button
      class="insight-card__retry-btn"
      data-testid="insight-card-retry"
      on:click={() => dispatch('retry')}
    >
      {$_('insights.card.retry')}
    </button>
  </article>

<!-- Happy path -->
{:else if insight}
  <article
    class="insight-card"
    data-testid="insight-card"
    data-expanded={expanded ? 'true' : 'false'}
    data-direction={dirClass}
  >
    <!-- ═══════════════ LEVEL 1 — always visible ═══════════════ -->
    <header class="insight-card__header">
      <span
        class="insight-card__direction insight-card__direction--{dirClass}"
        aria-hidden="true"
        data-testid="insight-card-direction"
      >{glyph}</span>

      <h3 class="insight-card__title" data-testid="insight-card-title">
        {title}
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

    <!-- Confidence scale (ADR-0018 — no raw % in collapsed view) -->
    <div class="insight-card__scale">
      <InsightConfidenceScale
        confidenceScore={insight.confidence}
        currentTier={insight.tier}
        entryCount={insight.sample_n ?? 0}
        loading={false}
        showRawPercent={expanded}
      />
    </div>

    <!-- One-sentence statement -->
    <p
      class="insight-card__statement"
      data-testid="insight-card-statement"
    >
      {insight.statement ?? $_('home.insight.empty_statement')}
    </p>

    <!-- Sample meta -->
    <p class="insight-card__meta" data-testid="insight-card-meta">
      {$_('insights.card.sample_meta', {
        values: {
          n: insight.sample_n ?? 0,
          days: insight.time_window_days ?? 0
        }
      })}
    </p>

    <!-- Disclaimer link (#168) -->
    <a
      href="/insights/disclaimer"
      class="insight-card__disclaimer"
      data-testid="insight-card-disclaimer"
      rel="noopener"
    >
      {$_('insights.card.disclaimer_link')} <span aria-hidden="true">ⓘ</span>
    </a>

    <!-- Expand / Collapse toggle -->
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

    <!-- ═══════════════ LEVEL 2 — expanded details ═══════════════ -->
    {#if expanded}
      <section
        id="insight-level2-{insight.id}"
        class="insight-card__level2"
        data-testid="insight-card-level2"
      >
        <!-- Dual-axis sparkline chart -->
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
            <!-- Y-axis grid lines -->
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
            <!-- Series A -->
            <polyline
              points={seriesA}
              fill="none"
              stroke="var(--color-primary)"
              stroke-width="1.5"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <!-- Series B -->
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
            <span class="insight-card__legend-label">{insight.tag_a ?? insight.factor_a ?? 'A'}</span>
            {#if (insight.tag_b ?? insight.factor_b)}
              <span class="insight-card__legend-dot insight-card__legend-dot--secondary"></span>
              <span class="insight-card__legend-label">{insight.tag_b ?? insight.factor_b}</span>
            {/if}
          </div>
        </div>

        <!-- Technical metadata -->
        <dl
          class="insight-card__meta-grid"
          data-testid="insight-card-tech-meta"
        >
          {#if insight.r_value != null}
            <div class="insight-card__meta-row">
              <dt>{$_('insights.card.meta_r')}</dt>
              <dd data-testid="insight-card-r-value">{insight.r_value.toFixed(3)}</dd>
            </div>
          {/if}
          {#if insight.rho_value != null}
            <div class="insight-card__meta-row">
              <dt>{$_('insights.card.meta_rho')}</dt>
              <dd>{insight.rho_value.toFixed(3)}</dd>
            </div>
          {/if}
          {#if insight.p_value != null}
            <div class="insight-card__meta-row">
              <dt>{$_('insights.card.meta_p')}</dt>
              <dd data-testid="insight-card-p-value">{insight.p_value < 0.001 ? '<0.001' : insight.p_value.toFixed(3)}</dd>
            </div>
          {/if}
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_confidence')}</dt>
            <dd data-testid="insight-card-confidence-raw">{(insight.confidence * 100).toFixed(0)}%</dd>
          </div>
          <div class="insight-card__meta-row">
            <dt>{$_('insights.card.meta_effect')}</dt>
            <dd>{insight.effect_size != null ? insight.effect_size.toFixed(3) : '—'}</dd>
          </div>
        </dl>

        <!-- CSV export stub (#169) -->
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
  /* ─── Card shell ─────────────────────────────────────────────── */
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

  /* ─── Header row ─────────────────────────────────────────────── */
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
  .insight-card__direction--positive { color: var(--color-success); }
  .insight-card__direction--negative { color: var(--color-notification); }
  .insight-card__direction--neutral  { color: var(--color-text-muted); }

  .insight-card__title {
    flex: 1;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 600;
    margin: 0;
    line-height: 1.3;
  }

  .insight-card__dismiss {
    flex-shrink: 0;
    padding: var(--space-1, 0.25rem);
    color: var(--color-text-muted);
    border-radius: var(--radius-sm, 0.375rem);
    font-size: 0.75rem;
    line-height: 1;
    transition: color var(--transition-interactive, 180ms ease),
                background var(--transition-interactive, 180ms ease);
  }
  .insight-card__dismiss:hover,
  .insight-card__dismiss:focus-visible {
    color: var(--color-text);
    background: var(--color-surface-offset);
  }

  /* ─── Statement & meta ───────────────────────────────────────── */
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

  /* ─── Disclaimer link ────────────────────────────────────────── */
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

  /* ─── Expand toggle ──────────────────────────────────────────── */
  .insight-card__toggle {
    display: flex;
    align-items: center;
    gap: var(--space-1, 0.25rem);
    align-self: flex-start;
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    color: var(--color-primary);
    padding: var(--space-1, 0.25rem) 0;
    border-radius: var(--radius-sm, 0.375rem);
    transition: color var(--transition-interactive, 180ms ease);
  }
  .insight-card__toggle:hover {
    color: var(--color-primary-hover);
  }

  .insight-card__toggle-icon {
    font-size: 0.6rem;
  }

  /* ─── Level 2 ────────────────────────────────────────────────── */
  .insight-card__level2 {
    display: flex;
    flex-direction: column;
    gap: var(--space-4, 1rem);
    padding-top: var(--space-3, 0.75rem);
    border-top: 1px solid oklch(from var(--color-text) l c h / 0.08);
    animation: fadeSlideIn 180ms ease both;
  }

  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* Sparkline chart */
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
  .insight-card__legend-dot--primary   { background: var(--color-primary); }
  .insight-card__legend-dot--secondary { background: var(--color-orange); }

  .insight-card__legend-label {
    font-size: var(--text-xs, 0.72rem);
    color: var(--color-text-muted);
  }

  /* Technical metadata grid */
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

  /* CSV export button */
  .insight-card__export-btn {
    align-self: flex-start;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    border: 1px solid oklch(from var(--color-text) l c h / 0.15);
    border-radius: var(--radius-sm, 0.375rem);
    padding: var(--space-1, 0.25rem) var(--space-3, 0.75rem);
    transition: color var(--transition-interactive, 180ms ease),
                border-color var(--transition-interactive, 180ms ease);
  }
  .insight-card__export-btn:hover {
    color: var(--color-text);
    border-color: oklch(from var(--color-text) l c h / 0.3);
  }

  /* ─── Skeleton ───────────────────────────────────────────────── */
  .insight-card--skeleton {
    pointer-events: none;
  }

  @keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
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

  .skeleton-heading { height: 1.1rem; width: 55%; }
  .skeleton-text    { height: 0.85rem; width: 100%; }
  .skeleton-track   { height: 0.55rem; width: 100%; border-radius: 999px; }

  /* ─── Error state ────────────────────────────────────────────── */
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

  /* ─── Reduced motion ─────────────────────────────────────────── */
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
