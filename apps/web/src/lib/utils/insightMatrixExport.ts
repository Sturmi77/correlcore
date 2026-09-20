/**
 * Client-side report exports for Ebene 4 (/insights/report).
 * PNG was previously embedded in InsightMatrix; PDF is new (Phase 5).
 */

import type { InsightResponse } from '$lib/api/insights';
import { matrixConfidencePercent, matrixEffectTone } from '$lib/utils/insightMatrixRows';

function themeColor(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Download selected matrix rows as a PNG chart (former InsightMatrix.exportPng). */
export function exportMatrixPng(rows: readonly InsightResponse[], filename: string): void {
  const canvas = document.createElement('canvas');
  canvas.width = 900;
  canvas.height = Math.max(220, rows.length * 56 + 96);
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const colors = {
    background: themeColor('--color-surface') || '#ffffff',
    text: themeColor('--color-text') || '#111111',
    muted: themeColor('--color-text-muted') || '#666666',
    success: themeColor('--color-success') || '#2a7a4b',
    error: themeColor('--color-error') || '#b00020',
  };

  ctx.fillStyle = colors.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = colors.text;
  ctx.font = '700 24px sans-serif';
  ctx.fillText('CorrelCore Report', 32, 44);
  ctx.font = '14px sans-serif';
  rows.forEach((row, index) => {
    const y = 88 + index * 52;
    const effect = row.effect_size ?? 0;
    const tone = matrixEffectTone(effect);
    ctx.fillStyle =
      tone === 'positive' ? colors.success : tone === 'negative' ? colors.error : colors.muted;
    ctx.fillRect(32, y - 18, Math.max(8, Math.abs(effect) * 280), 24);
    ctx.fillStyle = colors.text;
    ctx.fillText(row.subject_label ?? row.metric, 332, y);
    ctx.fillText(effect.toFixed(2), 560, y);
    ctx.fillText(matrixConfidencePercent(row.confidence), 650, y);
  });

  const link = document.createElement('a');
  link.href = canvas.toDataURL('image/png');
  link.download = filename;
  link.click();
}

function pdfEscape(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

/**
 * Minimal single-page PDF (Helvetica) for the report table — no extra dependency.
 * Aggregated rows only; never writes per-day raw entries.
 */
export function exportMatrixPdf(
  rows: readonly InsightResponse[],
  options: { title: string; subtitle: string; disclaimer: string; filename: string }
): void {
  const lines: string[] = [
    options.title,
    options.subtitle,
    '',
    ...rows.map((row) => {
      const effect = row.effect_size ?? 0;
      const conf = matrixConfidencePercent(row.confidence);
      return `${row.subject_label ?? '-'} | ${row.metric} | ${effect.toFixed(2)} | n=${row.sample_n} | ${conf}`;
    }),
    '',
    options.disclaimer,
  ];

  const contentLines = lines.map((line, index) => {
    const y = 800 - index * 16;
    return `BT /F1 10 Tf 40 ${y} Td (${pdfEscape(line.slice(0, 110))}) Tj ET`;
  });
  const stream = contentLines.join('\n');
  const streamLength = new TextEncoder().encode(stream).length;

  const objects: string[] = [];
  objects.push('1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj');
  objects.push('2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj');
  objects.push(
    '3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj'
  );
  objects.push(`4 0 obj<< /Length ${streamLength} >>stream\n${stream}\nendstream\nendobj`);
  objects.push('5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj');

  let pdf = '%PDF-1.4\n';
  const offsets: number[] = [0];
  for (const object of objects) {
    offsets.push(new TextEncoder().encode(pdf).length);
    pdf += `${object}\n`;
  }
  const xrefStart = new TextEncoder().encode(pdf).length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += '0000000000 65535 f \n';
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  const blob = new Blob([pdf], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = options.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '';
  const text = String(value);
  return /[",\n;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** The report's own rows, as data — never the account-wide export (#928 §Datenschutz). */
function reportRecords(rows: readonly InsightResponse[]): Record<string, unknown>[] {
  return rows.map((row) => ({
    subject: row.subject_label ?? '',
    subject_type: row.subject_type ?? '',
    metric: row.metric,
    insight_type: row.insight_type,
    effect_size: row.effect_size ?? null,
    confidence: row.confidence ?? null,
    confidence_percent: matrixConfidencePercent(row.confidence),
    sample_n: row.sample_n ?? null,
    tier: row.tier ?? null,
    generated_for_date: row.generated_for_date ?? null,
    statement: row.statement ?? '',
  }));
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/**
 * Export the selected report rows as CSV.
 *
 * Deliberately not `/export/csv`: that endpoint serialises the whole account,
 * including note text and exact dates. On a page framed as a handout for a
 * medical conversation, that button disclosed far more than the aggregated
 * report it appeared to offer (#928 L1 / Datenschutz-Impact).
 */
export function exportReportCsv(rows: readonly InsightResponse[], filename: string): void {
  const records = reportRecords(rows);
  const headers = [
    'subject',
    'subject_type',
    'metric',
    'insight_type',
    'effect_size',
    'confidence',
    'confidence_percent',
    'sample_n',
    'tier',
    'generated_for_date',
    'statement',
  ];
  const lines = [
    headers.join(','),
    ...records.map((record) => headers.map((key) => csvCell(record[key] as string)).join(',')),
  ];
  downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }), filename);
}

/** Export the selected report rows as JSON — the report only, not the account. */
export function exportReportJson(rows: readonly InsightResponse[], filename: string): void {
  const payload = {
    kind: 'correlcore-insight-report',
    generated_at: new Date().toISOString(),
    row_count: rows.length,
    rows: reportRecords(rows),
  };
  downloadBlob(
    new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' }),
    filename
  );
}

export function reportExportFilename(
  kind: 'png' | 'pdf' | 'csv' | 'json',
  date = new Date()
): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `correlcore-report-${yyyy}-${mm}-${dd}.${kind}`;
}
