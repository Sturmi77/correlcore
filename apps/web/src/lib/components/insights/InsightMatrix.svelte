<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';

  export let insights: InsightResponse[] = [];

  $: rows = insights
    .filter(
      (insight) =>
        insight.insight_type === 'pointbiserial' &&
        insight.effect_size !== null &&
        insight.confidence !== null &&
        insight.confidence >= 0.2
    )
    .sort((a, b) => Math.abs(b.effect_size ?? 0) - Math.abs(a.effect_size ?? 0));

  function tone(effect: number): 'positive' | 'negative' | 'neutral' {
    if (effect >= 0.15) return 'positive';
    if (effect <= -0.15) return 'negative';
    return 'neutral';
  }

  function percent(value: number | null): string {
    if (value === null) return '-';
    return `${Math.round(value * 100)}%`;
  }

  function exportPng(): void {
    const canvas = document.createElement('canvas');
    canvas.width = 900;
    canvas.height = Math.max(220, rows.length * 56 + 96);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#111827';
    ctx.font = '700 24px sans-serif';
    ctx.fillText('CorrelCore Insight Matrix', 32, 44);
    ctx.font = '14px sans-serif';
    rows.forEach((row, index) => {
      const y = 88 + index * 52;
      const effect = row.effect_size ?? 0;
      ctx.fillStyle =
        tone(effect) === 'positive'
          ? '#15803d'
          : tone(effect) === 'negative'
            ? '#b91c1c'
            : '#6b7280';
      ctx.fillRect(32, y - 18, Math.max(8, Math.abs(effect) * 280), 24);
      ctx.fillStyle = '#111827';
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

<section class="insight-matrix" data-testid="insight-matrix">
  <header class="insight-matrix__header">
    <div>
      <h2>{$_('insights.matrix.heading')}</h2>
      <p>{$_('insights.matrix.subtitle')}</p>
    </div>
    <button
      class="btn btn-sm variant-soft-primary"
      type="button"
      on:click={exportPng}
      disabled={!rows.length}
    >
      {$_('insights.matrix.export')}
    </button>
  </header>

  {#if rows.length}
    <div class="insight-matrix__table" role="table" aria-label={$_('insights.matrix.heading')}>
      <div class="insight-matrix__row insight-matrix__row--head" role="row">
        <span role="columnheader">{$_('insights.matrix.tag')}</span>
        <span role="columnheader">{$_('insights.matrix.metric')}</span>
        <span role="columnheader">{$_('insights.matrix.effect')}</span>
        <span role="columnheader">{$_('insights.matrix.confidence')}</span>
      </div>
      {#each rows as row}
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
            <span style={`width: ${Math.max(10, Math.abs(effect) * 120)}px`}></span>
            {effect.toFixed(2)}
          </span>
          <span role="cell">{percent(row.confidence)}</span>
        </div>
      {/each}
    </div>
  {:else}
    <p class="insight-matrix__empty">{$_('insights.matrix.empty')}</p>
  {/if}
</section>

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
    font-size: 0.85rem;
  }

  .insight-matrix__table {
    overflow-x: auto;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.55);
    border-radius: 0.45rem;
  }

  .insight-matrix__row {
    min-width: 42rem;
    display: grid;
    grid-template-columns: 1.4fr 1fr 1.1fr 0.8fr;
    gap: 0.75rem;
    align-items: center;
    padding: 0.6rem 0.75rem;
    border-top: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.35);
    font-size: 0.85rem;
  }

  .insight-matrix__row--head {
    border-top: 0;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
  }

  .insight-matrix__effect {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .insight-matrix__effect span {
    display: inline-block;
    height: 0.55rem;
    border-radius: 999px;
    background: rgb(var(--color-surface-400, 156 163 175));
  }

  .insight-matrix__row[data-tone='positive'] .insight-matrix__effect span {
    background: rgb(var(--color-success-500, 34 197 94));
  }

  .insight-matrix__row[data-tone='negative'] .insight-matrix__effect span {
    background: rgb(var(--color-error-500, 239 68 68));
  }

  @media (max-width: 520px) {
    .insight-matrix__header {
      flex-direction: column;
    }
  }
</style>
