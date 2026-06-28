import { describe, expect, it } from 'vitest';
import {
  compareDailyAxisLayoutFromRoot,
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
      rightPadding: 18,
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
});
