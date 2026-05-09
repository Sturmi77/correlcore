/**
 * Tests for the sparkline geometry builder (ADR-0014).
 */

import { describe, it, expect } from 'vitest';
import { buildSparkline, type SparklinePoint } from './sparkline';

function pts(values: (number | null)[]): SparklinePoint[] {
  return values.map((v, i) => ({ date: `2026-05-${String(i + 1).padStart(2, '0')}`, value: v }));
}

describe('buildSparkline — empty', () => {
  it('returns empty geometry for zero points', () => {
    const g = buildSparkline([], 280, 32, 1, 5);
    expect(g.coords).toHaveLength(0);
    expect(g.solidSegments).toHaveLength(0);
    expect(g.dashedSegments).toHaveLength(0);
    expect(g.width).toBe(280);
    expect(g.height).toBe(32);
  });
});

describe('buildSparkline — value scaling', () => {
  it('places min at bottom and max at top, with 2 px padding', () => {
    const g = buildSparkline(pts([1, 5]), 100, 32, 1, 5);
    expect(g.coords[0].y).toBe(32 - 2); // min = bottom (innerH+pad)
    expect(g.coords[1].y).toBe(2); // max = top (pad only)
  });

  it('clamps out-of-range values into [min, max]', () => {
    const g = buildSparkline(pts([0, 6]), 100, 32, 1, 5);
    expect(g.coords[0].y).toBe(32 - 2); // 0 clamped to 1 → bottom
    expect(g.coords[1].y).toBe(2); // 6 clamped to 5 → top
  });

  it('spaces points evenly over the width', () => {
    const g = buildSparkline(pts([1, 2, 3]), 200, 32, 1, 5);
    expect(g.coords[0].x).toBe(0);
    expect(g.coords[1].x).toBe(100);
    expect(g.coords[2].x).toBe(200);
  });

  it('centers a single point horizontally', () => {
    const g = buildSparkline(pts([3]), 200, 32, 1, 5);
    expect(g.coords[0].x).toBe(100);
    expect(g.coords[0].y).toBeGreaterThan(0);
  });
});

describe('buildSparkline — solid vs dashed segments', () => {
  it('builds solid segments between consecutive non-null points', () => {
    const g = buildSparkline(pts([1, 2, 3, 4, 5]), 400, 32, 1, 5);
    expect(g.solidSegments).toHaveLength(4);
    expect(g.dashedSegments).toHaveLength(0);
  });

  it('drops segments where one endpoint is missing', () => {
    const g = buildSparkline(pts([1, null, 3, 4]), 400, 32, 1, 5);
    // Solid segments: only (3→4). The (1→null) and (null→3) pairs
    // are not solid because one side is null.
    expect(g.solidSegments).toHaveLength(1);
    expect(g.solidSegments[0].x1).toBeCloseTo(g.coords[2].x);
    expect(g.solidSegments[0].x2).toBeCloseTo(g.coords[3].x);
  });

  it('bridges single-day gaps with a dashed segment', () => {
    const g = buildSparkline(pts([1, null, 3]), 200, 32, 1, 5);
    expect(g.dashedSegments).toHaveLength(1);
    expect(g.dashedSegments[0].x1).toBe(g.coords[0].x);
    expect(g.dashedSegments[0].x2).toBe(g.coords[2].x);
  });

  it('bridges multi-day gaps with a single dashed segment', () => {
    const g = buildSparkline(pts([1, null, null, null, 5]), 400, 32, 1, 5);
    expect(g.dashedSegments).toHaveLength(1);
    expect(g.dashedSegments[0].x1).toBe(g.coords[0].x);
    expect(g.dashedSegments[0].x2).toBe(g.coords[4].x);
  });

  it('does not draw bridges before the first known value', () => {
    const g = buildSparkline(pts([null, null, 3, 4]), 200, 32, 1, 5);
    // No bridges — first known value is index 2; nothing to bridge to its left.
    expect(g.dashedSegments).toHaveLength(0);
    // Only one solid segment between index 2 and 3.
    expect(g.solidSegments).toHaveLength(1);
  });

  it('exposes nulls in coords for missing days so the renderer skips circles', () => {
    const g = buildSparkline(pts([1, null, 3]), 200, 32, 1, 5);
    expect(g.coords[1].y).toBeNull();
    expect(g.coords[1].value).toBeNull();
  });
});

describe('buildSparkline — robustness', () => {
  it('treats NaN/Infinity as missing', () => {
    const g = buildSparkline(pts([Number.NaN, Number.POSITIVE_INFINITY, 3]), 200, 32, 1, 5);
    expect(g.coords[0].y).toBeNull();
    expect(g.coords[1].y).toBeNull();
    expect(g.coords[2].y).not.toBeNull();
  });

  it('survives a degenerate min == max range', () => {
    const g = buildSparkline(pts([3, 3]), 100, 32, 3, 3);
    // span clamped to 1 internally; both points should be at the top
    // because (v - min) / span = 0/1 = 0 → 1-0 = 1 → bottom.
    // Either way: no NaN, no crash.
    expect(g.coords).toHaveLength(2);
    expect(Number.isFinite(g.coords[0].y as number)).toBe(true);
  });
});
