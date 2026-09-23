/**
 * Client-side report exports for Ebene 4 (/insights/report).
 * PNG was previously embedded in InsightMatrix; PDF is new (Phase 5).
 */

import type { InsightReportRow } from '$lib/utils/insightReportRows';
import { matrixConfidencePercent, matrixEffectTone } from '$lib/utils/insightMatrixRows';

function themeColor(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface ReportRenderLabels {
  effect: string;
  with: string;
  without: string;
  total: string;
  confidence: string;
  window: string;
  missing: string;
}

const DEFAULT_RENDER_LABELS: ReportRenderLabels = {
  effect: 'effect',
  with: 'with',
  without: 'without',
  total: 'total',
  confidence: 'confidence',
  window: 'window',
  missing: '—',
};

function wrapCanvasText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let current = '';
  for (const char of text) {
    const candidate = current + char;
    if (current && ctx.measureText(candidate).width > maxWidth) {
      lines.push(current);
      current = char;
    } else {
      current = candidate;
    }
  }
  if (current || lines.length === 0) lines.push(current);
  return lines;
}

/** Download selected matrix rows as a PNG chart (former InsightMatrix.exportPng). */
export function exportMatrixPng(
  rows: readonly InsightReportRow[],
  filename: string,
  labels: ReportRenderLabels = DEFAULT_RENDER_LABELS
): void {
  const canvas = document.createElement('canvas');
  canvas.width = 1400;
  const measurementContext = canvas.getContext('2d');
  if (!measurementContext) return;
  measurementContext.font = '13px sans-serif';
  const prepared = rows.map((row) => ({
    row,
    factorLines: wrapCanvasText(measurementContext, row.factor ?? labels.missing, 280),
  }));
  const rowHeights = prepared.map(({ factorLines }) => Math.max(72, factorLines.length * 18 + 38));
  canvas.height = Math.max(
    220,
    rowHeights.reduce((total, height) => total + height, 110)
  );
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
  ctx.font = '13px sans-serif';
  let y = 94;
  prepared.forEach(({ row, factorLines }, index) => {
    const effect = row.effect ?? 0;
    const tone = matrixEffectTone(effect);
    ctx.fillStyle =
      tone === 'positive' ? colors.success : tone === 'negative' ? colors.error : colors.muted;
    ctx.fillRect(32, y - 18, Math.max(8, Math.abs(effect) * 210), 24);
    ctx.fillStyle = colors.text;
    factorLines.forEach((line, lineIndex) => ctx.fillText(line, 270, y + lineIndex * 18));
    ctx.fillText(row.metric, 570, y, 170);
    ctx.fillText(row.effect === null ? labels.missing : row.effect.toFixed(2), 760, y);
    ctx.fillText(
      `${labels.with} ${row.sampleWith ?? labels.missing} / ${labels.without} ${row.sampleWithout ?? labels.missing}`,
      850,
      y
    );
    ctx.fillText(`${labels.total} ${row.sampleTotal}`, 1080, y);
    const window =
      row.analysisWindowStart && row.analysisWindowEnd
        ? `${row.analysisWindowStart} – ${row.analysisWindowEnd}`
        : labels.missing;
    ctx.fillText(`${labels.window} ${window}`, 1180, y, 190);
    ctx.fillStyle = colors.muted;
    ctx.fillText(matrixConfidencePercent(row.confidence), 760, y + 22);
    y += rowHeights[index] ?? 72;
  });

  const link = document.createElement('a');
  link.href = canvas.toDataURL('image/png');
  link.download = filename;
  link.click();
}

/**
 * WinAnsi (CP1252) byte for the code points that are *not* simply the code
 * point itself. 0x00–0x7F and 0xA0–0xFF map one to one; this table is the
 * 0x80–0x9F block, where CP1252 puts typographic characters that Latin-1
 * leaves undefined — including the German quotes and the dashes our copy uses.
 */
const WIN_ANSI_EXCEPTIONS = new Map<number, number>([
  [0x20ac, 0x80],
  [0x201a, 0x82],
  [0x0192, 0x83],
  [0x201e, 0x84],
  [0x2026, 0x85],
  [0x2020, 0x86],
  [0x2021, 0x87],
  [0x02c6, 0x88],
  [0x2030, 0x89],
  [0x0160, 0x8a],
  [0x2039, 0x8b],
  [0x0152, 0x8c],
  [0x017d, 0x8e],
  [0x2018, 0x91],
  [0x2019, 0x92],
  [0x201c, 0x93],
  [0x201d, 0x94],
  [0x2022, 0x95],
  [0x2013, 0x96],
  [0x2014, 0x97],
  [0x02dc, 0x98],
  [0x2122, 0x99],
  [0x0161, 0x9a],
  [0x203a, 0x9b],
  [0x0153, 0x9c],
  [0x017e, 0x9e],
  [0x0178, 0x9f],
]);

/** Stand-in for a character WinAnsi has no byte for. */
const UNMAPPABLE = '?';

export type WinAnsiText = {
  /** One character per byte — `.length` is the byte count, as PDF needs. */
  text: string;
  /** True when at least one character had to be replaced. */
  lossy: boolean;
};

/**
 * Encode to WinAnsi, the encoding the font object declares (#960 option B).
 *
 * The document used to write UTF-8 bytes under a Helvetica with no `/Encoding`
 * at all, so the viewer fell back to StandardEncoding and every umlaut became
 * two stray glyphs — `Frühstück` read `Frˆ…hstˆ…ck`. For a German product that
 * is the normal case, and it hit exactly the user's own tag and symptom names.
 *
 * Switching the bytes alone is not enough: under StandardEncoding a Latin-1
 * `·` still renders as `•`. The `/Encoding /WinAnsiEncoding` entry on the font
 * is what makes the byte table match, so the two belong together.
 *
 * Returns a binary string (each char code is one byte) so that offsets and
 * `/Length` stay plain string arithmetic, and so the caller can hand the bytes
 * to a Blob without a UTF-8 round trip.
 */
export function toWinAnsi(text: string): WinAnsiText {
  let out = '';
  let lossy = false;
  for (const char of text) {
    const code = char.codePointAt(0) ?? 0;
    const mapped =
      code < 0x80 || (code >= 0xa0 && code <= 0xff) ? code : WIN_ANSI_EXCEPTIONS.get(code);
    if (mapped === undefined) {
      out += UNMAPPABLE;
      lossy = true;
      continue;
    }
    out += String.fromCharCode(mapped);
  }
  return { text: out, lossy };
}

function pdfEscape(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

/** Page box and text metrics of the generated PDF, in PDF user units. */
const PDF_PAGE_WIDTH = 612;
const PDF_PAGE_HEIGHT = 842;
const PDF_TOP_BASELINE = 800;
const PDF_LINE_HEIGHT = 16;
const PDF_BOTTOM_MARGIN = 56;

/**
 * Lines that fit between the first baseline and the bottom margin.
 *
 * The document used to be a single page with an unbounded downward cursor, so
 * from roughly this many lines on, the remaining rows *and the disclaimer* were
 * written outside the MediaBox and silently vanished — on a surface framed as a
 * handout for a doctor's appointment (#959).
 */
export const PDF_LINES_PER_PAGE =
  Math.floor((PDF_TOP_BASELINE - PDF_BOTTOM_MARGIN) / PDF_LINE_HEIGHT) + 1;

function paginate(lines: readonly string[]): string[][] {
  const pages: string[][] = [];
  for (let index = 0; index < lines.length; index += PDF_LINES_PER_PAGE) {
    pages.push(lines.slice(index, index + PDF_LINES_PER_PAGE));
  }
  return pages.length > 0 ? pages : [[]];
}

/**
 * Minimal multi-page PDF (Helvetica) for the report table — no extra dependency.
 * Aggregated rows only; never writes per-day raw entries.
 *
 * Exported separately from the download so the document itself is testable.
 */
export function buildMatrixPdfDocument(
  rows: readonly InsightReportRow[],
  options: {
    title: string;
    subtitle: string;
    disclaimer: string;
    charsetNote?: string;
    missingLabel?: string;
    labels?: Partial<ReportRenderLabels>;
  }
): string {
  const labels = { ...DEFAULT_RENDER_LABELS, ...options.labels };
  const missing = options.missingLabel ?? labels.missing;
  const sourceLines: string[] = [
    options.title,
    options.subtitle,
    '',
    ...rows.flatMap((row) => {
      const conf = matrixConfidencePercent(row.confidence);
      const window =
        row.analysisWindowStart && row.analysisWindowEnd
          ? `${row.analysisWindowStart}–${row.analysisWindowEnd}`
          : missing;
      const line = `${row.factor ?? missing} | ${row.metric} | ${labels.effect}=${row.effect === null ? missing : row.effect.toFixed(2)} | ${labels.with}=${row.sampleWith ?? missing} | ${labels.without}=${row.sampleWithout ?? missing} | ${labels.total}=${row.sampleTotal} | ${labels.confidence}=${conf} | ${labels.window}=${window}`;
      return line.match(/.{1,105}(?:\s|$)|\S{1,105}/g) ?? [line];
    }),
    '',
    options.disclaimer,
  ];

  const encoded = sourceLines.map((line) => toWinAnsi(line));
  const lines = encoded.map((entry) => entry.text);
  // A replaced character is visible as `?`, but only the document itself can
  // say why — and where the full labels are still readable (#960).
  if (encoded.some((entry) => entry.lossy) && options.charsetNote) {
    lines.push('', toWinAnsi(options.charsetNote.slice(0, 110)).text);
  }

  const pages = paginate(lines);
  // 1 catalog, 2 page tree, 3 font, then a page and a content object per page.
  const pageObjectIds = pages.map((_, index) => 4 + index * 2);

  const objects: string[] = [];
  objects.push('1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj');
  objects.push(
    `2 0 obj<< /Type /Pages /Kids [${pageObjectIds
      .map((id) => `${id} 0 R`)
      .join(' ')}] /Count ${pages.length} >>endobj`
  );
  // Without this entry the viewer falls back to StandardEncoding, where the
  // same bytes render as different glyphs — it is half of the fix, not a nicety.
  objects.push(
    '3 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>endobj'
  );
  pages.forEach((pageLines, index) => {
    const pageId = pageObjectIds[index];
    const contentId = pageId + 1;
    const stream = pageLines
      .map((line, lineIndex) => {
        const y = PDF_TOP_BASELINE - lineIndex * PDF_LINE_HEIGHT;
        return `BT /F1 10 Tf 40 ${y} Td (${pdfEscape(line)}) Tj ET`;
      })
      .join('\n');
    objects.push(
      `${pageId} 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PDF_PAGE_WIDTH} ${PDF_PAGE_HEIGHT}] /Contents ${contentId} 0 R /Resources << /Font << /F1 3 0 R >> >> >>endobj`
    );
    objects.push(
      `${contentId} 0 obj<< /Length ${stream.length} >>stream\n${stream}\nendstream\nendobj`
    );
  });

  // Every char in `pdf` is one byte from here on, so `.length` is the byte
  // offset the xref table needs; `exportMatrixPdf` widens it back to bytes.
  let pdf = '%PDF-1.4\n';
  const offsets: number[] = [0];
  for (const object of objects) {
    offsets.push(pdf.length);
    pdf += `${object}\n`;
  }
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += '0000000000 65535 f \n';
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  return pdf;
}

export function exportMatrixPdf(
  rows: readonly InsightReportRow[],
  options: {
    title: string;
    subtitle: string;
    disclaimer: string;
    charsetNote?: string;
    missingLabel?: string;
    labels?: Partial<ReportRenderLabels>;
    filename: string;
  }
): void {
  const pdf = buildMatrixPdfDocument(rows, options);
  // One char per byte. Handing the string straight to a Blob would UTF-8 it and
  // turn every WinAnsi byte above 0x7F back into the two the fix removed.
  const bytes = Uint8Array.from(pdf, (char) => char.charCodeAt(0) & 0xff);

  const blob = new Blob([bytes], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = options.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

type CsvCell = { kind: 'text'; value: string | null } | { kind: 'number'; value: number | null };

function startsWithSpreadsheetFormula(text: string): boolean {
  let index = 0;
  while (index < text.length && text.charCodeAt(index) <= 0x20) index += 1;
  const marker = text[index];
  return marker !== undefined && '=+-@'.includes(marker);
}

function csvCell(cell: CsvCell): string {
  if (cell.value === null) return '';
  if (cell.kind === 'number') return Number.isFinite(cell.value) ? String(cell.value) : '';
  // Spreadsheet programs ignore leading whitespace/control bytes while deciding
  // whether a cell is a formula. Prefix text whose first meaningful character
  // is a formula marker; quoting is a separate CSV concern and is applied after.
  const safe = startsWithSpreadsheetFormula(cell.value) ? `'${cell.value}` : cell.value;
  return /[",\r\n;]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

/** The report's own rows, as data — never the account-wide export (#928 §Datenschutz). */
function reportRecords(rows: readonly InsightReportRow[]): Record<string, CsvCell>[] {
  return rows.map((row) => ({
    factor: { kind: 'text', value: row.factor },
    factor_type: { kind: 'text', value: row.factorType },
    metric: { kind: 'text', value: row.metric },
    insight_type: { kind: 'text', value: row.insightType },
    effect_size: { kind: 'number', value: row.effect },
    confidence: { kind: 'number', value: row.confidence },
    sample_with: { kind: 'number', value: row.sampleWith },
    sample_without: { kind: 'number', value: row.sampleWithout },
    sample_total: { kind: 'number', value: row.sampleTotal },
    tier: { kind: 'text', value: row.tier },
    analysis_window_start: { kind: 'text', value: row.analysisWindowStart },
    analysis_window_end: { kind: 'text', value: row.analysisWindowEnd },
    generated_for_date: { kind: 'text', value: row.generatedForDate },
    statement: { kind: 'text', value: row.statement },
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
export function serializeReportCsv(rows: readonly InsightReportRow[]): string {
  const records = reportRecords(rows);
  const headers = [
    'factor',
    'factor_type',
    'metric',
    'insight_type',
    'effect_size',
    'confidence',
    'sample_with',
    'sample_without',
    'sample_total',
    'tier',
    'analysis_window_start',
    'analysis_window_end',
    'generated_for_date',
    'statement',
  ];
  const lines = [
    headers.join(','),
    ...records.map((record) => headers.map((key) => csvCell(record[key])).join(',')),
  ];
  return lines.join('\r\n');
}

export function exportReportCsv(rows: readonly InsightReportRow[], filename: string): void {
  downloadBlob(new Blob([serializeReportCsv(rows)], { type: 'text/csv;charset=utf-8' }), filename);
}

/** Export the selected report rows as JSON — the report only, not the account. */
export function buildReportJson(
  rows: readonly InsightReportRow[],
  generatedAt = new Date()
): string {
  const payload = {
    kind: 'correlcore-insight-report',
    generated_at: generatedAt.toISOString(),
    row_count: rows.length,
    rows,
  };
  return JSON.stringify(payload, null, 2);
}

export function exportReportJson(rows: readonly InsightReportRow[], filename: string): void {
  downloadBlob(
    new Blob([buildReportJson(rows)], { type: 'application/json;charset=utf-8' }),
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
