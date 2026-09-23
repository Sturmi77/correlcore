<script lang="ts">
  /**
   * /insights/report — Ebene 4 report surface (Phase 5 / ADR-0043).
   * Secondary route under Insights; export home for PNG/CSV/JSON/PDF.
   */
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import {
    listLatestInsights,
    type InsightMaturity,
    type InsightResponse,
  } from '$lib/api/insights';
  import {
    exportMatrixPdf,
    exportMatrixPng,
    exportReportCsv,
    exportReportJson,
    reportExportFilename,
  } from '$lib/utils/insightMatrixExport';
  import { buildMatrixDisplayRows } from '$lib/utils/insightMatrixRows';
  import { buildInsightReportRows, reportCoverageStats } from '$lib/utils/insightReportRows';
  import { MATRIX_INSIGHT_TYPES } from '$lib/utils/insightMatrixGate';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import InsightReportTable from '$lib/components/insights/InsightReportTable.svelte';
  import CorrelationHint from '$lib/components/insights/CorrelationHint.svelte';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let insights: InsightResponse[] = [];
  let maturity: InsightMaturity | null = null;
  let loading = true;
  let error: string | null = null;
  let selectedIds: string[] = [];
  /**
   * The initial "everything selected" is seeded once, by `seedSelection` after
   * a load that produced rows. It used to be a reactive refill of any empty
   * selection, which made clearing the last row — or unticking "select all" —
   * impossible and left the `export_empty` path unreachable (#959).
   */
  let selectionSeeded = false;
  let exportBusy: 'pdf' | 'png' | 'csv' | 'json' | null = null;
  let exportError: string | null = null;

  $: matrixRows = buildMatrixDisplayRows(insights, { includeWeak: false }).strong;
  $: reportRows = buildInsightReportRows(matrixRows);
  $: selectedRows = reportRows.filter((row) => selectedIds.includes(row.id));
  $: coverage = reportCoverageStats(selectedRows);

  /**
   * `?signal=<id>` preselects one row.
   *
   * "Remember for report" on the signal page used to be a bare link, so the
   * chosen signal had no effect here at all — and for a null association it
   * opened a report that filters that very signal out (#965).
   */
  $: requestedSignalId = $page.url.searchParams.get('signal');

  // Drop ids a reload no longer offers. An empty result of this pruning stays
  // empty — only `seedSelection` ever fills the selection.
  $: {
    const valid = new Set(reportRows.map((row) => row.id));
    const kept = selectedIds.filter((id) => valid.has(id));
    if (kept.length !== selectedIds.length) selectedIds = kept;
  }

  /** True when a signal was requested but is not among the reportable rows. */
  $: requestedSignalMissing = Boolean(
    requestedSignalId &&
    !loading &&
    !error &&
    !reportRows.some((row) => row.id === requestedSignalId)
  );

  /** Select everything (or the requested signal) once, on the first load with rows. */
  function seedSelection(): void {
    if (selectionSeeded) return;
    const rows = buildMatrixDisplayRows(insights, { includeWeak: false }).strong;
    if (rows.length === 0) return;
    selectedIds = requestedSignalId
      ? rows.some((row) => row.id === requestedSignalId)
        ? [requestedSignalId]
        : []
      : rows.map((row) => row.id);
    selectionSeeded = true;
  }

  async function loadReport(): Promise<void> {
    loading = true;
    error = null;
    try {
      // Filtered by family so the cap applies to reportable rows only: an
      // account with more than 50 analytical subjects used to lose valid rows —
      // or see an empty report — because unrelated families took the slots (#959).
      const response = await listLatestInsights({
        limit: 100,
        insightTypes: MATRIX_INSIGHT_TYPES,
      });
      insights = response.insights;
      maturity = response.insight_maturity;
      seedSelection();
    } catch (err) {
      error = err instanceof Error ? err.message : $_('insights.report.error');
      // Keep the rows a previous load produced. Clearing them here let the
      // pruning block drop every selected id on a transient refresh failure,
      // and seeding is one-shot — so the next success left everything
      // unchecked and every export reported `export_empty` (#959 review).
      // On the very first load there is nothing to keep.
    } finally {
      loading = false;
    }
  }

  function toggleRow(id: string, selected: boolean): void {
    if (selected) {
      if (!selectedIds.includes(id)) selectedIds = [...selectedIds, id];
      return;
    }
    selectedIds = selectedIds.filter((item) => item !== id);
  }

  function toggleAll(selected: boolean): void {
    selectedIds = selected ? reportRows.map((row) => row.id) : [];
  }

  function handlePng(): void {
    exportError = null;
    if (selectedRows.length === 0) {
      exportError = $_('insights.report.export_empty');
      return;
    }
    exportBusy = 'png';
    try {
      exportMatrixPng(selectedRows, reportExportFilename('png'), {
        effect: $_('insights.report.col_effect'),
        with: $_('insights.report.col_with'),
        without: $_('insights.report.col_without'),
        total: $_('insights.report.col_total'),
        confidence: $_('insights.report.col_confidence'),
        window: $_('insights.report.col_window'),
        missing: $_('insights.report.missing'),
      });
    } finally {
      exportBusy = null;
    }
  }

  function handlePdf(): void {
    exportError = null;
    if (selectedRows.length === 0) {
      exportError = $_('insights.report.export_empty');
      return;
    }
    exportBusy = 'pdf';
    try {
      exportMatrixPdf(selectedRows, {
        title: $_('insights.report.title'),
        subtitle: $_('insights.report.pdf_subtitle'),
        disclaimer: $_('insights.report.disclaimer'),
        // Only printed when a label actually lost a character (#960).
        charsetNote: $_('insights.report.pdf_charset_note'),
        missingLabel: $_('insights.report.missing'),
        labels: {
          effect: $_('insights.report.col_effect'),
          with: $_('insights.report.col_with'),
          without: $_('insights.report.col_without'),
          total: $_('insights.report.col_total'),
          confidence: $_('insights.report.col_confidence'),
          window: $_('insights.report.col_window'),
          missing: $_('insights.report.missing'),
        },
        filename: reportExportFilename('pdf'),
      });
    } finally {
      exportBusy = null;
    }
  }

  /**
   * Export the *report* as data.
   *
   * Previously this called `/export/csv` and `/export/json`, which serialise the
   * whole account — notes, exact dates, identity, every entry. On a surface
   * presented as a shareable handout that silently disclosed far more than the
   * aggregated report (#928). Now it writes the selected rows only.
   */
  function handleDataExport(kind: 'csv' | 'json'): void {
    exportError = null;
    exportBusy = kind;
    try {
      if (selectedRows.length === 0) {
        exportError = $_('insights.report.export_empty');
        return;
      }
      if (kind === 'csv') {
        exportReportCsv(selectedRows, reportExportFilename('csv'));
      } else {
        exportReportJson(selectedRows, reportExportFilename('json'));
      }
    } catch (err) {
      exportError = err instanceof Error ? err.message : $_('insights.report.export_error');
    } finally {
      exportBusy = null;
    }
  }

  onMount(() => {
    if ($auth.status !== 'authenticated') {
      const returnPath = requestedSignalId
        ? `/insights/report?signal=${encodeURIComponent(requestedSignalId)}`
        : '/insights/report';
      void goto(`/auth/login?next=${encodeURIComponent(returnPath)}`);
      return;
    }
    void loadReport();
    return registerPageRefresh(() => loadReport());
  });
</script>

<svelte:head>
  <title>{$_('insights.report.title')} - {$_('app.name')}</title>
</svelte:head>

<div class="report-page" data-testid="insights-report-page">
  <ScreenHeader
    title={$_('insights.report.title')}
    subtitle={$_('insights.report.subtitle')}
    back={{ href: '/insights', label: $_('nav.insights') }}
  />

  <div class="report-page__exports" role="group" aria-label={$_('insights.report.export_aria')}>
    <button
      type="button"
      class="btn btn-sm btn--primary"
      data-testid="insight-report-export-pdf"
      disabled={exportBusy !== null || loading}
      on:click={handlePdf}
    >
      {exportBusy === 'pdf' ? $_('insights.report.export_busy') : $_('insights.report.export_pdf')}
    </button>
    <button
      type="button"
      class="btn btn-sm btn--secondary"
      data-testid="insight-report-export-png"
      disabled={exportBusy !== null || loading}
      on:click={handlePng}
    >
      {exportBusy === 'png' ? $_('insights.report.export_busy') : $_('insights.report.export_png')}
    </button>
    <button
      type="button"
      class="btn btn-sm btn--secondary"
      data-testid="insight-report-export-csv"
      disabled={exportBusy !== null || loading}
      on:click={() => void handleDataExport('csv')}
    >
      {exportBusy === 'csv' ? $_('insights.report.export_busy') : $_('insights.report.export_csv')}
    </button>
    <button
      type="button"
      class="btn btn-sm btn--secondary"
      data-testid="insight-report-export-json"
      disabled={exportBusy !== null || loading}
      on:click={() => void handleDataExport('json')}
    >
      {exportBusy === 'json'
        ? $_('insights.report.export_busy')
        : $_('insights.report.export_json')}
    </button>
  </div>

  {#if requestedSignalMissing}
    <!--
      A null association, or any signal outside the report families, is not a
      reportable row. Silently falling back to "everything selected" would make
      the action look like it had worked (#965).
    -->
    <InlineAlert
      variant="info"
      message={$_('insights.report.signal_not_reportable')}
      testId="report-signal-missing"
    />
  {/if}
  {#if exportError}
    <InlineAlert variant="error" message={exportError} />
  {/if}
  {#if error}
    <InlineAlert variant="error" message={error} />
  {/if}

  {#if loading}
    <p class="report-page__status" role="status">{$_('insights.report.loading')}</p>
  {:else if reportRows.length === 0}
    <p class="report-page__status" data-testid="insight-report-empty">
      {$_('insights.report.empty')}
    </p>
  {:else}
    <section class="report-page__card" data-testid="insight-report-card">
      <header class="report-page__card-head">
        <div>
          <h2>{$_('insights.report.table_heading')}</h2>
          <p>{$_('insights.report.table_subtitle')}</p>
        </div>
        <p class="report-page__selection-hint">{$_('insights.report.selection_hint')}</p>
      </header>

      <InsightReportTable
        rows={reportRows}
        {selectedIds}
        {maturity}
        onToggle={toggleRow}
        onToggleAll={toggleAll}
      />

      <footer class="report-page__footer">
        <p class="report-page__coverage" data-testid="insight-report-coverage">
          {$_('insights.report.coverage', {
            values: { rows: coverage.rowCount, n: coverage.maxSampleN },
          })}
        </p>
        <p class="report-page__disclaimer" data-testid="insight-report-disclaimer">
          {$_('insights.report.disclaimer')}
        </p>
      </footer>
    </section>
  {/if}

  <div class="report-page__hint">
    <CorrelationHint returnTo="/insights/report" />
  </div>
</div>

<style>
  .report-page {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0 0 2rem;
  }

  .report-page__exports {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .report-page__status {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .report-page__card {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .report-page__card-head {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .report-page__card-head h2,
  .report-page__card-head p {
    margin: 0;
  }

  .report-page__card-head h2 {
    font-size: var(--text-lg, 1.1rem);
  }

  .report-page__card-head p,
  .report-page__selection-hint {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .report-page__footer {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--color-border-chart);
  }

  .report-page__coverage,
  .report-page__disclaimer {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .report-page__disclaimer {
    max-width: 28rem;
  }

  .report-page__hint {
    margin-top: 0.25rem;
  }
</style>
