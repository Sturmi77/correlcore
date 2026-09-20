import { describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { exportMatrixPdf, reportExportFilename } from './insightMatrixExport';

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
