import { describe, expect, it } from 'vitest';
import { buildMedianTrajectory, medianOfSorted, quantileOfSorted } from './medianTrajectory';

describe('medianOfSorted / quantileOfSorted', () => {
  it('computes odd and even medians', () => {
    expect(medianOfSorted([1, 2, 3])).toBe(2);
    expect(medianOfSorted([1, 2, 3, 4])).toBe(2.5);
  });

  it('interpolates quartiles', () => {
    expect(quantileOfSorted([1, 2, 3, 4], 0.25)).toBe(1.75);
    expect(quantileOfSorted([1, 2, 3, 4], 0.75)).toBe(3.25);
  });
});

describe('buildMedianTrajectory (#810)', () => {
  it('returns nulls when no values exist at an offset', () => {
    const traj = buildMedianTrajectory(
      [
        {
          cells: [
            { offset: -1, displayValue: null },
            { offset: 0, displayValue: null },
          ],
        },
      ],
      1
    );
    expect(traj).toEqual([
      { offset: -1, median: null, q1: null, q3: null, n: 0 },
      { offset: 0, median: null, q1: null, q3: null, n: 0 },
      { offset: 1, median: null, q1: null, q3: null, n: 0 },
    ]);
  });

  it('aggregates per-offset medians and IQR across rows', () => {
    const traj = buildMedianTrajectory(
      [
        {
          cells: [
            { offset: -1, displayValue: 1 },
            { offset: 0, displayValue: 2 },
            { offset: 1, displayValue: 4 },
          ],
        },
        {
          cells: [
            { offset: -1, displayValue: 3 },
            { offset: 0, displayValue: 4 },
            { offset: 1, displayValue: null },
          ],
        },
        {
          cells: [
            { offset: -1, displayValue: 5 },
            { offset: 0, displayValue: 6 },
            { offset: 1, displayValue: 8 },
          ],
        },
      ],
      1
    );

    expect(traj.find((c) => c.offset === -1)).toEqual({
      offset: -1,
      median: 3,
      q1: 2,
      q3: 4,
      n: 3,
    });
    expect(traj.find((c) => c.offset === 0)).toEqual({
      offset: 0,
      median: 4,
      q1: 3,
      q3: 5,
      n: 3,
    });
    expect(traj.find((c) => c.offset === 1)).toEqual({
      offset: 1,
      median: 6,
      q1: 5,
      q3: 7,
      n: 2,
    });
  });
});
