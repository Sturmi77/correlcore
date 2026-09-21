import { describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  buildMatrixPdfDocument,
  exportMatrixPdf,
  PDF_LINES_PER_PAGE,
  reportExportFilename,
  toWinAnsi,
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
    const offsets = [...pdf.matchAll(/^(\d{10}) 00000 n $/gm)].map((match) => Number(match[1]));

    expect(offsets.length).toBeGreaterThan(3);
    offsets.forEach((offset, index) => {
      // One char per byte, so a string index is the byte offset (#960).
      expect(pdf.slice(offset, offset + 16).startsWith(`${index + 1} 0 obj`)).toBe(true);
    });
  });

  it('declares each content stream with its real byte length', () => {
    // /Length is now computed per page. A stale or mismatched value is exactly
    // the kind of error a reader rejects the whole file over.
    const pdf = buildMatrixPdfDocument(rows(120), options);
    const streams = [...pdf.matchAll(/<< \/Length (\d+) >>stream\n([\s\S]*?)\nendstream/g)];

    expect(streams.length).toBeGreaterThan(1);
    for (const [, declared, body] of streams) {
      expect(body.length).toBe(Number(declared));
    }
  });

  it('writes the disclaimer inside the last page, not past its bottom edge', () => {
    const pdf = buildMatrixPdfDocument(rows(120), options);
    const lastStream = [...pdf.matchAll(/>>stream\n([\s\S]*?)\nendstream/g)].at(-1)?.[1] ?? '';
    const disclaimerLine = lastStream.split('\n').find((line) => line.includes(options.disclaimer));

    expect(disclaimerLine).toBeDefined();
    expect(Number(disclaimerLine?.match(/Tf 40 (-?\d+) Td/)?.[1])).toBeGreaterThan(0);
  });

  it('fits the documented number of lines per page', () => {
    // title + subtitle + blank + rows + blank + disclaimer
    const rowsThatFillOnePage = PDF_LINES_PER_PAGE - 5;

    expect(pageCount(buildMatrixPdfDocument(rows(rowsThatFillOnePage), options))).toBe(1);
    expect(pageCount(buildMatrixPdfDocument(rows(rowsThatFillOnePage + 1), options))).toBe(2);
  });
});

describe('toWinAnsi (#960)', () => {
  it('maps German text to one byte per character', () => {
    const { text, lossy } = toWinAnsi('Frühstück');

    expect(lossy).toBe(false);
    expect(text).toHaveLength('Frühstück'.length);
    expect([...text].map((char) => char.charCodeAt(0))).toEqual([
      0x46, 0x72, 0xfc, 0x68, 0x73, 0x74, 0xfc, 0x63, 0x6b,
    ]);
  });

  it('maps the typographic characters our copy uses, which Latin-1 lacks', () => {
    // German quotes, en/em dash and the ellipsis live in CP1252's 0x80–0x9F
    // block. Encoding as plain Latin-1 would drop them.
    expect([...toWinAnsi('„x" – y — z …').text].map((c) => c.charCodeAt(0))).toContain(0x84);
    expect(toWinAnsi('—').text.charCodeAt(0)).toBe(0x97);
    expect(toWinAnsi('…').text.charCodeAt(0)).toBe(0x85);
    expect(toWinAnsi('—').lossy).toBe(false);
  });

  it('keeps the middle dot as itself, not as a bullet', () => {
    // The byte is the same either way; what differs is the encoding the font
    // declares. Pinned here because switching bytes alone looked like a fix.
    expect(toWinAnsi('·').text.charCodeAt(0)).toBe(0xb7);
  });

  it('replaces what WinAnsi has no byte for, and says that it did', () => {
    const cyrillic = toWinAnsi('Кофе');
    expect(cyrillic.text).toBe('????');
    expect(cyrillic.lossy).toBe(true);

    const emoji = toWinAnsi('Sport 🧠');
    expect(emoji.text).toBe('Sport ?');
    expect(emoji.lossy).toBe(true);
  });

  it('counts an astral character once, not twice', () => {
    // Iterating by code unit would emit two replacements for one emoji and
    // desync the byte count from `/Length`.
    expect(toWinAnsi('🧠').text).toHaveLength(1);
  });
});

describe('buildMatrixPdfDocument character set (#960)', () => {
  const options = {
    title: 'Bericht',
    subtitle: 'CorrelCore Zusammenhänge-Bericht',
    disclaimer: 'Keine Diagnose.',
    charsetNote: 'Hinweis: Einzelne Zeichen konnten nicht dargestellt werden.',
  };

  function umlautRow(label: string): InsightResponse {
    return { ...row, subject_label: label };
  }

  it('declares WinAnsi on the font', () => {
    const pdf = buildMatrixPdfDocument([umlautRow('Frühstück')], options);

    expect(pdf).toContain('/BaseFont /Helvetica /Encoding /WinAnsiEncoding');
  });

  it('writes umlauts as single WinAnsi bytes, not as UTF-8 pairs', () => {
    const pdf = buildMatrixPdfDocument([umlautRow('Frühstück')], options);

    expect(pdf).toContain(`Fr\u00fchst\u00fcck`);
    // The UTF-8 pair for ü — what the document used to contain.
    expect(pdf).not.toContain(`\u00c3\u00bc`);
  });

  it('escapes PDF delimiters after encoding, not instead of it', () => {
    // A tag like this mixes both concerns: the parentheses must be escaped so
    // the string literal stays intact, and the umlauts must survive as bytes.
    const pdf = buildMatrixPdfDocument([umlautRow('Büro (Großraum)')], options);

    expect(pdf).toContain('B\u00fcro \\(Gro\u00dfraum\\)');
  });

  it('stays silent about the character set when nothing was replaced', () => {
    const pdf = buildMatrixPdfDocument([umlautRow('Erkältung')], options);

    expect(pdf).not.toContain('Hinweis');
  });

  it('adds the note once when a label lost a character', () => {
    const pdf = buildMatrixPdfDocument([umlautRow('Кофе'), umlautRow('Erkältung')], options);

    expect(pdf).toContain('????');
    expect(pdf.match(/Hinweis/g)).toHaveLength(1);
  });

  it('leaves the note out when the caller supplies none', () => {
    const pdf = buildMatrixPdfDocument([umlautRow('Кофе')], {
      title: options.title,
      subtitle: options.subtitle,
      disclaimer: options.disclaimer,
    });

    expect(pdf).toContain('????');
    expect(pdf).not.toContain('Hinweis');
  });
});
