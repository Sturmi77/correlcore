import { describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  buildMatrixPdfDocument,
  exportMatrixPdf,
  PDF_LINES_PER_PAGE,
  reportExportFilename,
} from './insightMatrixExport';

const row: InsightResponse = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'pointbiserial',
  tier: 'developing',
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 'sport',
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.7,
  sample_n: 24,
  statement: 'Sport lines up with higher mood.',
  flags: {},
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('reportExportFilename', () => {
  it('names report files by kind and date', () => {
    expect(reportExportFilename('pdf', new Date('2026-09-19T12:00:00Z'))).toBe(
      'correlcore-report-2026-09-19.pdf'
    );
  });
});

describe('exportMatrixPdf', () => {
  it('downloads a PDF blob for selected rows', () => {
    const click = vi.fn();
    const remove = vi.fn();
    const createElement = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') {
        return {
          click,
          remove,
          set href(_value: string) {},
          get href() {
            return '';
          },
          set download(_value: string) {},
          get download() {
            return '';
          },
        } as unknown as HTMLAnchorElement;
      }
      return document.createElementNS('http://www.w3.org/1999/xhtml', tag);
    });
    const createObjectURL = vi.fn((_blob: Blob) => 'blob:pdf');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    const appendChild = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);

    exportMatrixPdf([row], {
      title: 'Report',
      subtitle: 'Subtitle',
      disclaimer: 'Not a diagnosis.',
      filename: 'test.pdf',
    });

    expect(createObjectURL).toHaveBeenCalled();
    const blob = createObjectURL.mock.calls[0]?.[0];
    expect(blob?.type).toBe('application/pdf');
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:pdf');

    createElement.mockRestore();
    appendChild.mockRestore();
    vi.unstubAllGlobals();
  });
});

describe('buildMatrixPdfDocument pagination (#959)', () => {
  const options = {
    title: 'CorrelCore Report',
    subtitle: 'Aggregated correlations',
    disclaimer: 'Associations in your entries, not a cause.',
  };

  function rows(count: number): InsightResponse[] {
    return Array.from({ length: count }, (_, index) => ({
      ...row,
      id: `insight-${index}`,
      subject_label: `Subject ${index}`,
    }));
  }

  function pageCount(pdf: string): number {
    return Number(pdf.match(/\/Type \/Pages [^>]*\/Count (\d+)/)?.[1] ?? 0);
  }

  it('keeps a short report on one page', () => {
    const pdf = buildMatrixPdfDocument(rows(3), options);

    expect(pageCount(pdf)).toBe(1);
    expect(pdf).toContain(options.disclaimer);
  });

  it('breaks a full selection across pages instead of dropping the overflow', () => {
    // The route selects up to 50 rows; the old single page fit ~47 lines, so a
    // valid full selection lost rows and the disclaimer without any notice.
    const pdf = buildMatrixPdfDocument(rows(50), options);

    expect(pageCount(pdf)).toBeGreaterThan(1);
    for (let index = 0; index < 50; index += 1) {
      expect(pdf).toContain(`Subject ${index} `);
    }
    expect(pdf).toContain(options.disclaimer);
  });

  it('writes every line inside the page box', () => {
    const pdf = buildMatrixPdfDocument(rows(120), options);
    const baselines = [...pdf.matchAll(/Tf 40 (-?\d+) Td/g)].map((match) => Number(match[1]));

    expect(baselines.length).toBeGreaterThan(0);
    expect(Math.min(...baselines)).toBeGreaterThan(0);
    expect(Math.max(...baselines)).toBeLessThan(842);
  });

  it('declares one page object per page, with matching kids', () => {
    const pdf = buildMatrixPdfDocument(rows(120), options);
    const pages = pageCount(pdf);
    const kids = pdf
      .match(/\/Kids \[([^\]]*)\]/)?.[1]
      ?.trim()
      .split(/\s+0 R\s*/)
      .filter(Boolean);

    expect(kids).toHaveLength(pages);
    expect([...pdf.matchAll(/\/Type \/Page[^s]/g)]).toHaveLength(pages);
  });

  it('keeps the xref table pointing at each object it declares', () => {
    // Object numbering is now dynamic (one page + one content stream per page),
    // so an off-by-one in the offsets would produce a file readers reject.
    const pdf = buildMatrixPdfDocument(rows(120), options);
    const bytes = new TextEncoder().encode(pdf);
    const offsets = [...pdf.matchAll(/^(\d{10}) 00000 n $/gm)].map((match) => Number(match[1]));

    expect(offsets.length).toBeGreaterThan(3);
    offsets.forEach((offset, index) => {
      const head = new TextDecoder().decode(bytes.slice(offset, offset + 16));
      expect(head.startsWith(`${index + 1} 0 obj`)).toBe(true);
    });
  });

  it('fits the documented number of lines per page', () => {
    // title + subtitle + blank + rows + blank + disclaimer
    const rowsThatFillOnePage = PDF_LINES_PER_PAGE - 5;

    expect(pageCount(buildMatrixPdfDocument(rows(rowsThatFillOnePage), options))).toBe(1);
    expect(pageCount(buildMatrixPdfDocument(rows(rowsThatFillOnePage + 1), options))).toBe(2);
  });
});
