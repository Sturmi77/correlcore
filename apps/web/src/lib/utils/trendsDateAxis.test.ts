import { describe, expect, it } from 'vitest';
import {
  clampAxisRangeToData,
  compareDailyAxisLayoutFromRoot,
  habitDailyAxisLayout,
  trendsDayAxisMetrics,
  trendsDayCenterX,
  trendsPlotWidth,
  toDailyAxisLayout,
} from './trendsDateAxis';

describe('trendsDateAxis', () => {
  const metrics = trendsDayAxisMetrics(16);

  it('maps rem metrics to DailyAxisLayout', () => {
    expect(toDailyAxisLayout(metrics)).toEqual({
      labelWidth: 112,
      dayWidth: 13.12,
      dayGap: 2.88,
      rightPadding: 0,
    });
  });

  it('computes aligned day centers and plot width', () => {
    expect(trendsDayCenterX(0, metrics)).toBeCloseTo(112 + 6.56, 1);
    expect(trendsDayCenterX(1, metrics)).toBeCloseTo(112 + 13.12 + 2.88 + 6.56, 1);
    expect(trendsPlotWidth(3, metrics)).toBeCloseTo(112 + 3 * 13.12 + 2 * 2.88, 1);
  });

  it('scales with root font size', () => {
    const layout = compareDailyAxisLayoutFromRoot(20);
    expect(layout.dayWidth).toBeCloseTo(0.82 * 20);
    expect(layout.labelWidth).toBeCloseTo(7 * 20);
  });

  it('habitDailyAxisLayout defaults to the compare day pitch (Phase 11 / O3)', () => {
    expect(habitDailyAxisLayout()).toEqual(compareDailyAxisLayoutFromRoot(16));
  });

  it('habitDailyAxisLayout preserves compact and coarse densities', () => {
    expect(habitDailyAxisLayout({ compact: true })).toEqual({
      labelWidth: 4.5 * 16,
      dayWidth: 0.65 * 16,
      dayGap: 0.15 * 16,
      rightPadding: 0,
    });
    expect(habitDailyAxisLayout({ coarsePointer: true })).toEqual({
      labelWidth: 7 * 16,
      dayWidth: 2.75 * 16,
      dayGap: 0.25 * 16,
      rightPadding: 0,
    });
    // Compact wins over coarse when both are set (Habits detail sheet).
    expect(habitDailyAxisLayout({ compact: true, coarsePointer: true }).dayWidth).toBe(0.65 * 16);
  });

  describe('clampAxisRangeToData (#676)', () => {
    it('trims a 365d window down to the data extent on both ends', () => {
      // Window spans the whole year, but data only exists mid-window.
      expect(
        clampAxisRangeToData('2026-01-01', '2026-12-31', ['2026-06-10', '2026-06-11', '2026-06-20'])
      ).toEqual({ start: '2026-06-10', end: '2026-06-20' });
    });

    it('keeps raw bounds when they sit inside the data extent', () => {
      // Raw window is already narrower than the data — do not widen it.
      expect(
        clampAxisRangeToData('2026-06-15', '2026-06-18', ['2026-06-10', '2026-06-20'])
      ).toEqual({ start: '2026-06-15', end: '2026-06-18' });
    });

    it('is unaffected by data-date order', () => {
      expect(
        clampAxisRangeToData('2026-01-01', '2026-12-31', ['2026-06-20', '2026-06-10', '2026-06-11'])
      ).toEqual({ start: '2026-06-10', end: '2026-06-20' });
    });

    it('collapses to a single day when only one day has data', () => {
      expect(clampAxisRangeToData('2026-01-01', '2026-12-31', ['2026-06-10'])).toEqual({
        start: '2026-06-10',
        end: '2026-06-10',
      });
    });

    it('returns the raw window unchanged when there is no data', () => {
      expect(clampAxisRangeToData('2026-01-01', '2026-12-31', [])).toEqual({
        start: '2026-01-01',
        end: '2026-12-31',
      });
    });

    it('falls back to the data extent when the raw window is empty', () => {
      expect(clampAxisRangeToData('', '', ['2026-06-10', '2026-06-20'])).toEqual({
        start: '2026-06-10',
        end: '2026-06-20',
      });
    });

    it('falls back to the data extent when the raw window lies entirely after the data', () => {
      // max(rawStart, first)=2026-07-01 > min(rawEnd, last)=2026-06-20 would invert.
      expect(
        clampAxisRangeToData('2026-07-01', '2026-07-31', ['2026-06-10', '2026-06-20'])
      ).toEqual({ start: '2026-06-10', end: '2026-06-20' });
    });
  });
});
