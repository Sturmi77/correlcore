/**
 * Chart adapter tests — M3.8 Sprint 2 (ADR-0035).
 *
 * Verifies that the divergent token resolver and StripCellMapper return
 * theme-token references (never hardcoded hues), and that midpoint /
 * dead-band semantics behave as documented in the ADR.
 */

import { describe, expect, it } from 'vitest';
import {
  StripCellMapper,
  adapterMetadata,
  lazyLoadLayerChart,
  resolveDivergentToken,
} from './index';

describe('resolveDivergentToken', () => {
  it('returns the neutral token inside the dead band', () => {
    const encoded = resolveDivergentToken(0);
    expect(encoded.color).toBe('var(--color-divergent-mid)');
    expect(encoded.opacity).toBe(0);
    expect(encoded.sign).toBe('mid');
  });

  it('returns the negative token for values below -0.0625', () => {
    const encoded = resolveDivergentToken(-0.5);
    expect(encoded.color).toBe('var(--color-divergent-neg)');
    expect(encoded.sign).toBe('neg');
    expect(encoded.opacity).toBeGreaterThan(0.25);
    expect(encoded.opacity).toBeLessThan(1);
  });

  it('returns the positive token for values above +0.0625', () => {
    const encoded = resolveDivergentToken(0.75);
    expect(encoded.color).toBe('var(--color-divergent-pos)');
    expect(encoded.sign).toBe('pos');
  });

  it('clamps values outside [-1, +1]', () => {
    const high = resolveDivergentToken(5);
    const low = resolveDivergentToken(-5);
    expect(high.opacity).toBe(1);
    expect(low.opacity).toBe(1);
  });

  it('treats non-finite input as neutral', () => {
    expect(resolveDivergentToken(Number.NaN).sign).toBe('mid');
    expect(resolveDivergentToken(Number.POSITIVE_INFINITY).sign).toBe('mid');
  });

  it('never returns a hardcoded hue (theme-agnostic guard, ADR-0035 §10)', () => {
    const samples = [-1, -0.5, -0.1, 0, 0.1, 0.5, 1];
    for (const v of samples) {
      const encoded = resolveDivergentToken(v);
      expect(encoded.color.startsWith('var(--color-')).toBe(true);
    }
  });
});

describe('StripCellMapper', () => {
  it('encodes mood values around midpoint=3 with range=4 correctly', () => {
    const mapper = new StripCellMapper({ midpoint: 3, range: 4 });

    expect(mapper.encode(3).sign).toBe('mid');
    expect(mapper.encode(5).sign).toBe('pos');
    expect(mapper.encode(1).sign).toBe('neg');
  });

  it('treats null / undefined / NaN as neutral with zero opacity', () => {
    const mapper = new StripCellMapper({ midpoint: 3, range: 4 });

    expect(mapper.encode(null).sign).toBe('mid');
    expect(mapper.encode(undefined).sign).toBe('mid');
    expect(mapper.encode(Number.NaN).sign).toBe('mid');
    expect(mapper.encode(null).opacity).toBe(0);
  });

  it('produces stronger opacity the further the value is from the midpoint', () => {
    const mapper = new StripCellMapper({ midpoint: 3, range: 4 });

    const near = mapper.encode(3.5);
    const far = mapper.encode(5);

    expect(far.opacity).toBeGreaterThan(near.opacity);
  });
});

describe('lazyLoadLayerChart', () => {
  it('returns null while the dependency is not yet installed', async () => {
    const mod = await lazyLoadLayerChart();
    expect(mod).toBeNull();
  });
});

describe('adapterMetadata', () => {
  it('declares a positive bundle budget', () => {
    expect(adapterMetadata.bundleBudgetGzKb).toBeGreaterThan(0);
    expect(adapterMetadata.name).toBe('correlcore-chart-adapter');
  });
});
