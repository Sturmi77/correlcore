import { describe, expect, it } from 'vitest';
import {
  SPLIT_LABEL_PARTNER_MAX_CHARS,
  buildSplitMedianTrajectories,
  splitRowsByPartner,
  truncatePartnerForRowLabel,
  type SplitSourceRow,
} from './esmSplitMedian';

const RADIUS = 7;

/** One window with a flat value at every offset, so medians are easy to read. */
function windowRow(onset: string, value: number): SplitSourceRow {
  const cells = [];
  for (let offset = -RADIUS; offset <= RADIUS; offset += 1) {
    cells.push({ offset, displayValue: value });
  }
  return { onset, cells };
}

describe('splitRowsByPartner (#920)', () => {
  const rows = [windowRow('2026-05-10', 4), windowRow('2026-06-20', 2)];

  it('assigns a window whose onset day carries the partner', () => {
    const split = splitRowsByPartner(rows, ['2026-05-10'], RADIUS);
    expect(split.withPartner.map((row) => row.onset)).toEqual(['2026-05-10']);
    expect(split.withoutPartner.map((row) => row.onset)).toEqual(['2026-06-20']);
  });

  it('counts a partner at the very edge of the window as present', () => {
    // onset + 7 is the last rendered offset, so it still belongs to the window.
    const split = splitRowsByPartner(rows, ['2026-05-17'], RADIUS);
    expect(split.withPartner.map((row) => row.onset)).toEqual(['2026-05-10']);
  });

  it('keeps a partner one day outside the window in the other branch', () => {
    const split = splitRowsByPartner(rows, ['2026-05-18'], RADIUS);
    expect(split.withPartner).toHaveLength(0);
    expect(split.withoutPartner).toHaveLength(2);
  });

  it('puts every window in the without-branch when the partner never appears', () => {
    const split = splitRowsByPartner(rows, [], RADIUS);
    expect(split.withoutPartner).toHaveLength(2);
  });
});

describe('buildSplitMedianTrajectories (#920)', () => {
  const withRows = ['2026-05-01', '2026-05-20', '2026-06-08'].map((onset) => windowRow(onset, 4));
  const withoutRows = ['2026-07-01', '2026-07-20', '2026-08-08'].map((onset) =>
    windowRow(onset, 2)
  );
  const presence = withRows.map((row) => row.onset);

  it('draws both branches once each clears the occurrence floor', () => {
    const split = buildSplitMedianTrajectories([...withRows, ...withoutRows], presence, RADIUS);

    expect(split.withPartner.windows).toBe(3);
    expect(split.withoutPartner.windows).toBe(3);
    expect(split.withPartner.cells?.[0]?.median).toBe(4);
    expect(split.withoutPartner.cells?.[0]?.median).toBe(2);
  });

  it('withholds the curve for a branch below the floor but keeps its count', () => {
    const sparse = [...withRows, windowRow('2026-07-01', 2), windowRow('2026-07-20', 2)];
    const split = buildSplitMedianTrajectories(sparse, presence, RADIUS);

    expect(split.withoutPartner.windows).toBe(2);
    expect(split.withoutPartner.cells).toBeNull();
    expect(split.withPartner.cells).not.toBeNull();
  });

  it('reports both branches as insufficient rather than inventing one curve', () => {
    const tiny = [windowRow('2026-05-01', 4), windowRow('2026-07-01', 2)];
    const split = buildSplitMedianTrajectories(tiny, ['2026-05-01'], RADIUS);

    expect(split.withPartner.cells).toBeNull();
    expect(split.withoutPartner.cells).toBeNull();
    expect(split.withPartner.windows).toBe(1);
    expect(split.withoutPartner.windows).toBe(1);
  });

  it('shortens a long partner name so the branch qualifier survives', () => {
    const long = 'Cold brew coffee with oat milk';
    const short = truncatePartnerForRowLabel(long);

    expect(short.length).toBeLessThanOrEqual(SPLIT_LABEL_PARTNER_MAX_CHARS);
    expect(short.endsWith('…')).toBe(true);
    expect(truncatePartnerForRowLabel('Coffee')).toBe('Coffee');
  });

  it('keeps the branch medians apart instead of averaging them together', () => {
    const split = buildSplitMedianTrajectories([...withRows, ...withoutRows], presence, RADIUS);
    const withMedian = split.withPartner.cells?.[3]?.median;
    const withoutMedian = split.withoutPartner.cells?.[3]?.median;

    expect(withMedian).not.toBe(withoutMedian);
    // The combined median would have been 3 — the point of the split.
    expect([withMedian, withoutMedian]).toEqual([4, 2]);
  });
});
