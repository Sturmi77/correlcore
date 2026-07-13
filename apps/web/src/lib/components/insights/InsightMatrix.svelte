<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';
  import { refreshTags, tags } from '$lib/stores/tags';

  export let insights: InsightResponse[] = [];

  type MatrixLayer = 'tags' | 'symptoms' | 'habits';

  let layer: MatrixLayer = 'tags';

  onMount(async () => {
    if ($tags.status === 'idle') {
      try {
        await refreshTags();
      } catch {
        /* matrix still works for tag insights without habit metadata */
      }
    }
  });

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

  function isMatrixInsight(insight: InsightResponse): boolean {
    return (
      (insight.insight_type === 'pointbiserial' ||
        insight.insight_type === 'symptom_mood_association') &&
      insight.effect_size !== null &&
      insight.confidence !== null &&
      insight.confidence >= 0.2
    );
  }

  $: habitTagIds = new Set(
    $tags.status === 'ready'
      ? $tags.tags.filter((tag) => tag.habit_type !== 'none').map((tag) => tag.id)
      : []
  );

  $: baseRows = dedupeRows(insights.filter(isMatrixInsight)).sort(
    (a, b) => Math.abs(b.effect_size ?? 0) - Math.abs(a.effect_size ?? 0)
  );

  $: rows = baseRows.filter((row) => {
    if (layer === 'symptoms') return row.subject_type === 'symptom';
    const isHabit =
      row.subject_type === 'tag' && row.subject_id !== null && habitTagIds.has(row.subject_id);
    if (layer === 'habits') return isHabit;
    return row.subject_type === 'tag' && !isHabit;
  });

  $: subjectHeading =
    layer === 'symptoms'
      ? $_('insights.matrix.subject_symptom')
      : layer === 'habits'
        ? $_('insights.matrix.subject_habit')
        : $_('insights.matrix.subject_tag');

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

<section class="insight-matrix" data-testid="insight-matrix">
  <header class="insight-matrix__header">
    <div>
      <h2>{$_('insights.matrix.heading')}</h2>
      <p>{$_('insights.matrix.subtitle')}</p>
    </div>
    <div class="insight-matrix__actions">
      <div class="insight-matrix__layers" role="tablist" aria-label={$_('insights.matrix.layers')}>
        {#each ['tags', 'symptoms', 'habits'] as option}
          <button
            type="button"
            role="tab"
            class="insight-matrix__layer"
            class:insight-matrix__layer--active={layer === option}
            aria-selected={layer === option}
            data-testid={`insight-matrix-layer-${option}`}
            on:click={() => (layer = option as MatrixLayer)}
          >
            {$_(`insights.matrix.layer_${option}`)}
          </button>
        {/each}
      </div>
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

  {#if rows.length}
    <div class="insight-matrix__table" role="table" aria-label={$_('insights.matrix.heading')}>
      <div class="insight-matrix__row insight-matrix__row--head" role="row">
        <span role="columnheader">{subjectHeading}</span>
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
    <p class="insight-matrix__empty">{$_('insights.matrix.empty_layer')}</p>
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

  .insight-matrix__actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.5rem;
  }

  .insight-matrix__layers {
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.35rem;
    padding: 0.2rem;
    border-radius: 999px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-2);
  }

  .insight-matrix__layer {
    min-height: 44px;
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: var(--color-text-muted);
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.75rem;
    cursor: pointer;
  }

  .insight-matrix__layer--active {
    background: var(--color-primary-soft);
    color: var(--color-primary);
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
    border: 1px solid var(--color-border-chart);
    border-radius: 0.45rem;
  }

  .insight-matrix__row {
    min-width: 42rem;
    display: grid;
    grid-template-columns: 1.4fr 1fr 1.1fr 0.8fr;
    gap: 0.75rem;
    align-items: center;
    padding: 0.6rem 0.75rem;
    border-top: 1px solid var(--color-border-chart);
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
    background: var(--color-text-muted);
  }

  .insight-matrix__row[data-tone='positive'] .insight-matrix__effect span {
    background: var(--color-success);
  }

  .insight-matrix__row[data-tone='negative'] .insight-matrix__effect span {
    background: var(--color-error);
  }

  @media (max-width: 520px) {
    .insight-matrix__header,
    .insight-matrix__actions {
      flex-direction: column;
      align-items: stretch;
    }

    .insight-matrix__layers {
      justify-content: flex-start;
    }
  }
</style>
