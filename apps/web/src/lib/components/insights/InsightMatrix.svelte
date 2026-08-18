<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { isMatrixInsight, isWeakMatrixInsight } from '$lib/utils/insightMatrixGate';

  export let insights: InsightResponse[] = [];
  /**
   * Marketing preview mode (landing product shot): hide the header/toolbar and
   * let the matrix rows fill the narrow frame, so the diagram is the hero (#546).
   */
  export let preview = false;

  function canonicalMetric(insight: InsightResponse): string {
    if (
      insight.subject_type === 'tag' &&
      ['mood', 'mood_score', 'mood_avg'].includes(insight.metric)
    ) {
      return 'mood_score';
    }
    return insight.metric;
  }

  function normaliseLabel(value: string): string {
    return value.toLocaleLowerCase().trim().replace(/\s+/g, ' ');
  }

  function rowKey(insight: InsightResponse): string {
    const tagSlug =
      typeof insight.payload?.tag_slug === 'string' ? normaliseLabel(insight.payload.tag_slug) : '';
    const subject =
      insight.subject_type === 'tag'
        ? tagSlug ||
          (insight.subject_label ? normaliseLabel(insight.subject_label) : '') ||
          insight.subject_id ||
          ''
        : insight.subject_id || insight.subject_label || '';
    return [
      insight.insight_type,
      canonicalMetric(insight),
      insight.subject_type ?? '',
      subject,
    ].join(':');
  }

  function strongerRow(left: InsightResponse, right: InsightResponse): InsightResponse {
    const leftEffect = Math.abs(left.effect_size ?? 0);
    const rightEffect = Math.abs(right.effect_size ?? 0);
    if (leftEffect !== rightEffect) return leftEffect > rightEffect ? left : right;
    const leftConfidence = left.confidence ?? 0;
    const rightConfidence = right.confidence ?? 0;
    if (leftConfidence !== rightConfidence) return leftConfidence > rightConfidence ? left : right;
    return left.generated_at >= right.generated_at ? left : right;
  }

  function dedupeRows(items: InsightResponse[]): InsightResponse[] {
    const byKey = new Map<string, InsightResponse>();
    for (const insight of items) {
      const key = rowKey(insight);
      const existing = byKey.get(key);
      byKey.set(key, existing ? strongerRow(existing, insight) : insight);
    }
    return [...byKey.values()];
  }

  function byEffectDesc(a: InsightResponse, b: InsightResponse): number {
    return Math.abs(b.effect_size ?? 0) - Math.abs(a.effect_size ?? 0);
  }

  // #725: dedupe once across all renderable rows, then split into reliable
  // (strong) and weakened bands so a subject never appears in both.
  $: displayRows = dedupeRows(
    insights.filter((insight) => isMatrixInsight(insight) || isWeakMatrixInsight(insight))
  );
  $: rows = displayRows.filter(isMatrixInsight).sort(byEffectDesc);
  $: weakRows = preview ? [] : displayRows.filter(isWeakMatrixInsight).sort(byEffectDesc);

  // #725 transparency: surface when the matrix was last recomputed, so lines
  // shifting after a regenerate read as an update rather than a glitch.
  function formatUpdated(iso: string): string {
    const parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return '';
    return new Intl.DateTimeFormat($locale ?? undefined, { dateStyle: 'medium' }).format(parsed);
  }

  $: lastUpdated = [...rows, ...weakRows].reduce<string>(
    (latest, row) => (row.generated_at > latest ? row.generated_at : latest),
    ''
  );
  $: lastUpdatedLabel = lastUpdated ? formatUpdated(lastUpdated) : '';

  function tone(effect: number): 'positive' | 'negative' | 'neutral' {
    if (effect >= 0.15) return 'positive';
    if (effect <= -0.15) return 'negative';
    return 'neutral';
  }

  function percent(value: number | null): string {
    if (value === null) return '-';
    return `${Math.round(value * 100)}%`;
  }

  function themeColor(name: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function exportPng(): void {
    const canvas = document.createElement('canvas');
    canvas.width = 900;
    canvas.height = Math.max(220, rows.length * 56 + 96);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const colors = {
      background: themeColor('--color-surface'),
      text: themeColor('--color-text'),
      muted: themeColor('--color-text-muted'),
      success: themeColor('--color-success'),
      error: themeColor('--color-error'),
    };

    ctx.fillStyle = colors.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = colors.text;
    ctx.font = '700 24px sans-serif';
    ctx.fillText('CorrelCore Insight Matrix', 32, 44);
    ctx.font = '14px sans-serif';
    rows.forEach((row, index) => {
      const y = 88 + index * 52;
      const effect = row.effect_size ?? 0;
      ctx.fillStyle =
        tone(effect) === 'positive'
          ? colors.success
          : tone(effect) === 'negative'
            ? colors.error
            : colors.muted;
      ctx.fillRect(32, y - 18, Math.max(8, Math.abs(effect) * 280), 24);
      ctx.fillStyle = colors.text;
      ctx.fillText(row.subject_label ?? row.metric, 332, y);
      ctx.fillText(effect.toFixed(2), 560, y);
      ctx.fillText(percent(row.confidence), 650, y);
    });

    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = 'correlcore-insight-matrix.png';
    link.click();
  }
</script>

<section
  class="insight-matrix"
  class:insight-matrix--preview={preview}
  data-testid="insight-matrix"
>
  {#if !preview}
    <header class="insight-matrix__header">
      <div>
        <h2>{$_('insights.matrix.heading')}</h2>
        <p>{$_('insights.matrix.subtitle')}</p>
        {#if lastUpdatedLabel}
          <p class="insight-matrix__updated" data-testid="insight-matrix-updated">
            {$_('insights.matrix.updated', { values: { date: lastUpdatedLabel } })}
          </p>
        {/if}
      </div>
      <div class="insight-matrix__actions">
        <button
          class="btn btn-sm btn--secondary"
          type="button"
          on:click={exportPng}
          disabled={!rows.length}
        >
          {$_('insights.matrix.export')}
        </button>
      </div>
    </header>
  {/if}

  {#if rows.length}
    {@render matrixTable(rows, !preview, 'insight-matrix-table', $_('insights.matrix.heading'))}
  {:else if weakRows.length}
    <p class="insight-matrix__empty">{$_('insights.matrix.empty_strong')}</p>
  {:else}
    <p class="insight-matrix__empty">{$_('insights.matrix.empty')}</p>
  {/if}

  {#if weakRows.length}
    <details class="insight-matrix__weak" data-testid="insight-matrix-weak">
      <summary class="insight-matrix__weak-toggle">
        {$_('insights.matrix.weak_toggle', { values: { count: weakRows.length } })}
      </summary>
      <p class="insight-matrix__weak-note">{$_('insights.matrix.weak_note')}</p>
      {@render matrixTable(
        weakRows,
        false,
        'insight-matrix-weak-table',
        $_('insights.matrix.weak_toggle', { values: { count: weakRows.length } })
      )}
    </details>
  {/if}
</section>

{#snippet matrixTable(
  tableRows: InsightResponse[],
  scrollable: boolean,
  testId: string,
  ariaLabel: string
)}
  <div
    class="insight-matrix__table"
    class:insight-matrix__table--scrollable={scrollable}
    role="table"
    aria-label={ariaLabel}
    data-testid={testId}
  >
    <div class="insight-matrix__row insight-matrix__row--head" role="row">
      <span role="columnheader">{$_('insights.matrix.subject')}</span>
      <span role="columnheader">{$_('insights.matrix.metric')}</span>
      <span role="columnheader">{$_('insights.matrix.effect')}</span>
      <span role="columnheader">{$_('insights.matrix.confidence')}</span>
    </div>
    {#each tableRows as row}
      {@const effect = row.effect_size ?? 0}
      <div
        class="insight-matrix__row"
        role="row"
        data-tone={tone(effect)}
        title={`${row.statement ?? ''} | n=${row.sample_n} | confidence=${percent(row.confidence)}`}
      >
        <span role="cell">{row.subject_label ?? '-'}</span>
        <span role="cell">{row.metric}</span>
        <span role="cell" class="insight-matrix__effect">
          <span
            class="insight-matrix__effect-bar"
            style={`--effect: ${Math.min(1, Math.abs(effect))}`}
          ></span>
          {effect.toFixed(2)}
        </span>
        <span role="cell">{percent(row.confidence)}</span>
      </div>
    {/each}
  </div>
{/snippet}

<style>
  .insight-matrix {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .insight-matrix__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  .insight-matrix__actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.5rem;
  }

  .insight-matrix__header h2,
  .insight-matrix__header p,
  .insight-matrix__empty {
    margin: 0;
  }

  .insight-matrix__header h2 {
    font-size: var(--text-lg, 1.1rem);
  }

  .insight-matrix__header p,
  .insight-matrix__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .insight-matrix__updated {
    margin-top: 0.25rem;
    font-size: var(--text-xs);
  }

  .insight-matrix__table {
    overflow-x: auto;
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    /* Prevent the fixed row min-width from widening the page shell. */
    max-width: 100%;
  }

  /* #628: long correlation lists stay fully reachable inside the matrix
     instead of clipping under the fixed bottom nav with no scroll affordance. */
  .insight-matrix__table--scrollable {
    max-height: min(70dvh, 32rem);
    overflow-y: auto;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .insight-matrix__row {
    min-width: 42rem;
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1.1fr) minmax(0, 0.8fr);
    gap: 0.75rem;
    align-items: center;
    padding: 0.6rem 0.75rem;
    border-top: 1px solid var(--color-border-chart);
    font-size: var(--text-sm);
  }

  .insight-matrix__row > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .insight-matrix__row--head {
    border-top: 0;
    font-size: var(--text-2xs);
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
  }

  .insight-matrix__table--scrollable .insight-matrix__row--head {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--color-surface-chart-bg, var(--color-surface));
  }

  .insight-matrix__effect {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .insight-matrix__effect-bar {
    display: inline-block;
    flex: 0 1 auto;
    width: calc(var(--effect, 0) * 7.5rem);
    max-width: 45%;
    min-width: 0.4rem;
    height: 0.55rem;
    border-radius: var(--radius-full);
    background: var(--color-text-muted);
  }

  .insight-matrix__row[data-tone='positive'] .insight-matrix__effect-bar {
    background: var(--color-success);
  }

  .insight-matrix__row[data-tone='negative'] .insight-matrix__effect-bar {
    background: var(--color-error);
  }

  /* #725: weakened correlations stay reachable in a collapsed disclosure
     instead of making the whole matrix disappear. Muted so they read as
     "below the reliability threshold", not as headline findings. */
  .insight-matrix__weak {
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    padding: 0.25rem 0.5rem;
  }

  .insight-matrix__weak-toggle {
    cursor: pointer;
    padding: 0.35rem 0.25rem;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text-muted);
  }

  .insight-matrix__weak-note {
    margin: 0.25rem 0.25rem 0.5rem;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .insight-matrix__weak .insight-matrix__table {
    opacity: 0.75;
  }

  @media (max-width: 767px) {
    /* Drop the desktop 42rem floor so four columns fit portrait without
       forcing page-level horizontal scroll (same idea as --preview). */
    .insight-matrix__row {
      min-width: 0;
      gap: 0.4rem;
      padding: 0.5rem 0.6rem;
      font-size: var(--text-xs);
      grid-template-columns: minmax(0, 1.5fr) minmax(0, 0.85fr) minmax(0, 1.15fr) minmax(0, 0.7fr);
    }

    .insight-matrix__row--head {
      font-size: var(--text-2xs);
      letter-spacing: 0.02em;
    }

    .insight-matrix__effect {
      gap: 0.35rem;
    }

    .insight-matrix__effect-bar {
      width: calc(var(--effect, 0) * 4.5rem);
      max-width: 40%;
      height: 0.45rem;
    }
  }

  @media (max-width: 480px) {
    .insight-matrix__header,
    .insight-matrix__actions {
      flex-direction: column;
      align-items: stretch;
    }

    /* Metric labels are secondary on narrow phones — keep subject + effect. */
    .insight-matrix__row {
      grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.2fr) minmax(0, 0.75fr);
    }

    .insight-matrix__row > span:nth-child(2) {
      display: none;
    }
  }

  /* Marketing preview (#546): no header, so the rows fill the narrow frame and
     the effect bars read as the hero. Drop the wide min-width so the four
     columns fit the product-shot column instead of scrolling out of view. */
  .insight-matrix--preview {
    gap: 0;
  }

  .insight-matrix--preview .insight-matrix__row {
    min-width: 0;
    gap: 0.4rem;
    padding: 0.5rem;
    font-size: var(--text-xs);
  }
</style>
