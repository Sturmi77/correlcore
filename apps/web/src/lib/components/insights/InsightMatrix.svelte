<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { buildMatrixDisplayRows, matrixRowTone } from '$lib/utils/insightMatrixRows';
  import InsightEvidence from './InsightEvidence.svelte';

  export let insights: InsightResponse[] = [];
  /**
   * Marketing preview mode (landing product shot): hide the header/toolbar and
   * let the matrix rows fill the narrow frame, so the diagram is the hero (#546).
   */
  export let preview = false;

  // #725: dedupe once across all renderable rows, then split into reliable
  // (strong) and weakened bands so a subject never appears in both.
  // Export lives on /insights/report (Phase 5 / ADR-0043 Ebene 4) — not here.
  $: matrixRows = buildMatrixDisplayRows(insights, { includeWeak: !preview });
  $: rows = matrixRows.strong;
  $: weakRows = matrixRows.weak;

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

  function tone(row: InsightResponse): 'positive' | 'negative' | 'neutral' {
    return matrixRowTone(row);
  }

  /** Phase 1 / D3 — natural frequencies with two denominators when payload has them. */
  function freqLabel(row: InsightResponse): string {
    const withN = row.payload?.tagged_count;
    const withoutN = row.payload?.untagged_count;
    if (typeof withN !== 'number' || typeof withoutN !== 'number') {
      return $_('insights.matrix.freq_sample', { values: { n: row.sample_n } });
    }
    return $_('insights.matrix.freq_split', {
      values: { withN, withoutN },
    });
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
        <p class="insight-matrix__report-link">
          <a href="/insights/report" data-testid="insight-matrix-report-link">
            {$_('insights.matrix.report_link')}
          </a>
        </p>
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
      <span role="columnheader">{$_('insights.matrix.frequency')}</span>
      <span role="columnheader">{$_('insights.matrix.confidence')}</span>
    </div>
    {#each tableRows as row}
      {@const effect = row.effect_size ?? 0}
      <div
        class="insight-matrix__row"
        role="row"
        data-tone={tone(row)}
        title={`${row.statement ?? ''} | ${freqLabel(row)}`}
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
        <span role="cell" class="insight-matrix__freq" data-testid="insight-matrix-freq">
          {freqLabel(row)}
        </span>
        <span role="cell" class="insight-matrix__confidence">
          <InsightEvidence
            confidenceScore={row.confidence ?? 0}
            currentTier={row.tier}
            entryCount={row.sample_n}
            showSample
            showMaturityBadge={false}
          />
        </span>
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

  .insight-matrix__report-link {
    margin-top: 0.5rem;
    font-size: var(--text-sm);
  }

  .insight-matrix__report-link a {
    color: var(--color-primary);
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
    min-width: 48rem;
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.9fr) minmax(0, 1fr) minmax(0, 1.1fr) minmax(
        0,
        1.4fr
      );
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

  .insight-matrix__freq {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .insight-matrix__confidence :global(.evidence) {
    flex-wrap: wrap;
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
    .insight-matrix__header {
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
