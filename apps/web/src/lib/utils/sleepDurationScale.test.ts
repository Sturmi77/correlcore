import { describe, expect, it } from 'vitest';

import {
  formatSleepMinutes,
  sleepDurationScale,
  SLEEP_BASELINE_MIN_DAYS,
  SLEEP_SPREAD_FLOOR_MINUTES,
} from './sleepDurationScale';

/** N nights of the given length, enough to clear the baseline threshold. */
function nights(minutes: number[], repeats = 1): number[] {
  return Array.from({ length: repeats }, () => minutes).flat();
}

describe('sleepDurationScale', () => {
  it('falls back to a sequential ramp while there is no usable baseline', () => {
    const scale = sleepDurationScale(nights([420], SLEEP_BASELINE_MIN_DAYS - 1));

    expect(scale.mode).toBe('sequential');
    expect(scale.loggedDays).toBe(SLEEP_BASELINE_MIN_DAYS - 1);
  });

  it("uses the user's own median as the neutral point once history allows", () => {
    // Seven 6h nights and seven 8h nights — median lands between them.
    const scale = sleepDurationScale([...nights([360], 7), ...nights([480], 7)]);

    expect(scale.mode).toBe('divergent');
    if (scale.mode !== 'divergent') return;
    expect(scale.medianMinutes).toBe(420);
    expect(scale.loggedDays).toBe(14);
  });

  it('does not read 6 h as neutral for a short sleeper (#928 D3)', () => {
    // The scale this replaced put its midpoint at exactly 360 min, so every
    // one of these nights would have rendered on the "negative" side.
    const scale = sleepDurationScale(nights([300], SLEEP_BASELINE_MIN_DAYS));

    expect(scale.mode).toBe('divergent');
    if (scale.mode !== 'divergent') return;
    expect(scale.medianMinutes).toBe(300);
  });

  it('floors the spread so a flat stretch does not saturate on minutes', () => {
    const scale = sleepDurationScale([...nights([420], 13), 430]);

    expect(scale.mode).toBe('divergent');
    if (scale.mode !== 'divergent') return;
    expect(scale.spreadMinutes).toBe(SLEEP_SPREAD_FLOOR_MINUTES);
  });

  it('stretches to the most unusual night when the spread is real', () => {
    const scale = sleepDurationScale([...nights([420], 13), 660]);

    expect(scale.mode).toBe('divergent');
    if (scale.mode !== 'divergent') return;
    expect(scale.medianMinutes).toBe(420);
    expect(scale.spreadMinutes).toBe(240);
  });

  it('counts only nights that were actually logged', () => {
    const scale = sleepDurationScale([
      ...nights([420], 10),
      null,
      undefined,
      Number.NaN,
      ...nights([420], 3),
    ]);

    expect(scale.loggedDays).toBe(13);
    expect(scale.mode).toBe('sequential');
  });

  it('reports an empty window without inventing a range', () => {
    const scale = sleepDurationScale([null, undefined]);

    expect(scale).toEqual({ mode: 'sequential', loggedDays: 0, minMinutes: 0, maxMinutes: 0 });
  });
});

describe('formatSleepMinutes', () => {
  it.each([
    [0, '0 min'],
    [45, '45 min'],
    [360, '6 h'],
    [430, '7 h 10 min'],
    [429.6, '7 h 10 min'],
  ])('formats %i minutes as %s', (minutes, expected) => {
    expect(formatSleepMinutes(minutes)).toBe(expected);
  });
});
