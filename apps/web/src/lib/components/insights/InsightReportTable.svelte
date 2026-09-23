<script lang="ts">
  /**
   * InsightReportTable — Phase 5 / Ebene 4 printable association table.
   * Row selection feeds PNG/PDF export; confidence uses InsightEvidence only.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity } from '$lib/api/insights';
  import type { InsightReportRow } from '$lib/utils/insightReportRows';
  import InsightEvidence from './InsightEvidence.svelte';
  import { matrixConfidencePercent, matrixEffectTone } from '$lib/utils/insightMatrixRows';

  export let rows: InsightReportRow[] = [];
  export let selectedIds: readonly string[] = [];
  export let maturity: InsightMaturity | null = null;
  export let onToggle: (id: string, selected: boolean) => void = () => undefined;
  export let onToggleAll: (selected: boolean) => void = () => undefined;

  $: selectedSet = new Set(selectedIds);
  $: allSelected = rows.length > 0 && rows.every((row) => selectedSet.has(row.id));

  function metricLabel(metric: string): string {
    if (metric === 'mood' || metric === 'mood_score' || metric === 'mood_avg') {
      return $_('trends.metric.mood');
    }
    if (metric === 'energy' || metric === 'energy_avg') return $_('trends.metric.energy');
    if (metric === 'stress' || metric === 'stress_avg') return $_('trends.metric.stress');
    if (metric === 'sleep_minutes') return $_('trends.metric.sleep_minutes');
    if (metric === 'sleep_quality') return $_('trends.metric.sleep_quality');
    return metric;
  }

  function countLabel(value: number | null): string {
    return value === null ? $_('insights.report.missing') : String(value);
  }

  function windowLabel(row: InsightReportRow): string {
    if (!row.analysisWindowStart || !row.analysisWindowEnd) return $_('insights.report.missing');
    return `${row.analysisWindowStart} – ${row.analysisWindowEnd}`;
  }
</script>

<div
  class="report-table"
  role="table"
  aria-label={$_('insights.report.table_aria')}
  data-testid="insight-report-table"
>
  <div class="report-table__row report-table__row--head" role="row">
    <span role="columnheader" class="report-table__select">
      <input
        type="checkbox"
        checked={allSelected}
        aria-label={$_('insights.report.select_all')}
        data-testid="insight-report-select-all"
        on:change={(event) => onToggleAll(event.currentTarget.checked)}
      />
    </span>
    <span role="columnheader">{$_('insights.report.col_factor')}</span>
    <span role="columnheader">{$_('insights.report.col_metric')}</span>
    <span role="columnheader">{$_('insights.report.col_effect')}</span>
    <span role="columnheader">{$_('insights.report.col_with')}</span>
    <span role="columnheader">{$_('insights.report.col_without')}</span>
    <span role="columnheader">{$_('insights.report.col_total')}</span>
    <span role="columnheader">{$_('insights.report.col_window')}</span>
    <span role="columnheader">{$_('insights.report.col_confidence')}</span>
  </div>

  {#each rows as row (row.id)}
    {@const effect = row.effect ?? 0}
    <div
      class="report-table__row"
      role="row"
      data-tone={matrixEffectTone(effect)}
      data-testid={`insight-report-row-${row.id}`}
    >
      <span role="cell" class="report-table__select">
        <input
          type="checkbox"
          checked={selectedSet.has(row.id)}
          aria-label={$_('insights.report.select_row', {
            values: { label: row.factor ?? row.metric },
          })}
          on:change={(event) => onToggle(row.id, event.currentTarget.checked)}
        />
      </span>
      <span role="cell">{row.factor ?? $_('insights.report.missing')}</span>
      <span role="cell">{metricLabel(row.metric)}</span>
      <span role="cell" class="report-table__effect">
        <span class="report-table__effect-bar" style={`--effect: ${Math.min(1, Math.abs(effect))}`}
        ></span>
        {row.effect === null
          ? $_('insights.report.missing')
          : `${effect >= 0 ? '+' : ''}${effect.toFixed(2)}`}
      </span>
      <span role="cell" class="report-table__freq">{countLabel(row.sampleWith)}</span>
      <span role="cell" class="report-table__freq">{countLabel(row.sampleWithout)}</span>
      <span role="cell" class="report-table__freq">{row.sampleTotal}</span>
      <span role="cell" class="report-table__freq">{windowLabel(row)}</span>
      <span role="cell" class="report-table__evidence">
        <!--
          The badge's label comes from the account-wide maturity phase, so its
          number has to come from there too. The row's sample made it read
          "Stable · 12 entries" off a phase reached from a different total — and
          that same 12 already sits in the coverage column (#965).
        -->
        <InsightEvidence
          {maturity}
          showMaturityBadge={Boolean(maturity)}
          confidenceScore={row.confidence ?? 0}
          currentTier={row.tier}
          entryCount={maturity?.current_entries ?? row.sampleTotal}
          showSample={false}
        />
        <span class="report-table__conf-pct">{matrixConfidencePercent(row.confidence)}</span>
      </span>
    </div>
  {/each}
</div>

<style>
  .report-table {
    overflow-x: auto;
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    max-width: 100%;
  }

  .report-table__row {
    min-width: 76rem;
    display: grid;
    grid-template-columns:
      2rem minmax(0, 1.25fr) minmax(0, 1fr) minmax(0, 0.8fr) repeat(3, minmax(0, 0.65fr))
      minmax(0, 1.5fr) minmax(0, 1.4fr);
    gap: 0.65rem;
    align-items: center;
    padding: 0.55rem 0.75rem;
    border-top: 1px solid var(--color-border-chart);
    font-size: var(--text-sm);
  }

  .report-table__row--head {
    border-top: none;
    font-weight: 600;
    color: var(--color-text-muted);
    background: var(--color-surface-elevated, var(--color-surface));
  }

  .report-table__row > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .report-table__select {
    display: flex;
    justify-content: center;
  }

  .report-table__effect {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-variant-numeric: tabular-nums;
  }

  .report-table__effect-bar {
    width: calc(var(--effect, 0) * 3.5rem);
    height: 0.55rem;
    border-radius: var(--radius-sm); /* token-exempt: 2px micro-bar; sm is closest token */
    background: var(--color-text-muted);
    flex-shrink: 0;
  }

  .report-table__row[data-tone='positive'] .report-table__effect-bar {
    background: var(--color-success);
  }

  .report-table__row[data-tone='negative'] .report-table__effect-bar {
    background: var(--color-error);
  }

  .report-table__freq {
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }

  .report-table__evidence {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }

  .report-table__conf-pct {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
  }
</style>
