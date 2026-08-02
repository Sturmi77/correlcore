import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./healthConnect', () => ({
  readHealthConnectSleepAndHeartRate: vi.fn(),
}));
vi.mock('$lib/api/healthConnect', () => ({
  importHealthConnectSleep: vi.fn(),
}));

import { importHealthConnectSleep } from '$lib/api/healthConnect';
import type { ConsentListResponse } from '$lib/api/consents';
import { readHealthConnectSleepAndHeartRate } from './healthConnect';
import { aggregateSleepByDate, syncHealthConnectSleep } from './healthConnectSync';

const granted = {
  current: [{ consent_type: 'health_connect', granted: true }],
} as unknown as ConsentListResponse;
const revoked = {
  current: [{ consent_type: 'health_connect', granted: false }],
} as unknown as ConsentListResponse;

const range = { start: '2026-07-03T00:00:00Z', end: '2026-08-02T00:00:00Z' };

describe('aggregateSleepByDate', () => {
  it('merges overlapping sessions ending at the same instant instead of double-counting', () => {
    // Two data origins (e.g. phone + wearable) both recorded the same night,
    // one session nested inside the other. Naively summing durations would
    // report 540 minutes; the real overlap is only 480.
    const map = aggregateSleepByDate([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 480 },
      { startTime: 'y', endTime: '2026-08-02T06:00:00Z', durationMinutes: 60 },
    ]);
    expect(map.size).toBe(1);
    expect([...map.values()][0]).toBe(480);
  });

  it('sums genuinely separate, non-overlapping sessions on the same wake-date', () => {
    const map = aggregateSleepByDate([
      // Main night sleep, ending on the wake-date.
      { startTime: '2026-08-01T22:00:00Z', endTime: '2026-08-02T06:00:00Z', durationMinutes: 480 },
      // A brief return-to-sleep later the same morning that doesn't overlap it.
      { startTime: '2026-08-02T07:00:00Z', endTime: '2026-08-02T07:30:00Z', durationMinutes: 30 },
    ]);
    expect(map.size).toBe(1);
    expect([...map.values()][0]).toBe(510);
  });

  it('clamps a day total to 1440 minutes', () => {
    const map = aggregateSleepByDate([
      // Two non-overlapping sessions, both ending on the same wake-date, whose
      // combined duration exceeds a day.
      { startTime: '2026-08-01T14:00:00Z', endTime: '2026-08-02T02:00:00Z', durationMinutes: 720 },
      { startTime: '2026-08-02T08:00:00Z', endTime: '2026-08-02T22:00:00Z', durationMinutes: 840 },
    ]);
    expect([...map.values()][0]).toBe(1440);
  });

  it('keeps sessions on different days separate', () => {
    const map = aggregateSleepByDate([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 400 },
      // 48h later — a different local date in every timezone
      { startTime: 'y', endTime: '2026-08-04T06:00:00Z', durationMinutes: 420 },
    ]);
    expect(map.size).toBe(2);
  });
});

describe('syncHealthConnectSleep', () => {
  beforeEach(() => {
    vi.mocked(readHealthConnectSleepAndHeartRate).mockReset();
    vi.mocked(importHealthConnectSleep).mockReset();
  });
  afterEach(() => vi.clearAllMocks());

  it('refuses without consent and never reads the bridge', async () => {
    const result = await syncHealthConnectSleep(revoked, range);
    expect(result.status).toBe('no_consent');
    expect(readHealthConnectSleepAndHeartRate).not.toHaveBeenCalled();
  });

  it('reports unavailable when the bridge returns null', async () => {
    vi.mocked(readHealthConnectSleepAndHeartRate).mockResolvedValue(null);
    const result = await syncHealthConnectSleep(granted, range);
    expect(result.status).toBe('unavailable');
    expect(importHealthConnectSleep).not.toHaveBeenCalled();
  });

  it('reports no_data when there are no sleep records', async () => {
    vi.mocked(readHealthConnectSleepAndHeartRate).mockResolvedValue({ sleep: [], heartRate: [] });
    const result = await syncHealthConnectSleep(granted, range);
    expect(result.status).toBe('no_data');
    expect(importHealthConnectSleep).not.toHaveBeenCalled();
  });

  it('aggregates and imports sleep when records are present', async () => {
    vi.mocked(readHealthConnectSleepAndHeartRate).mockResolvedValue({
      sleep: [{ startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 }],
      heartRate: [],
    });
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 1,
      skipped_existing_value: 0,
      skipped_no_entry: 0,
      sleep_sync_enabled: true,
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('ok');
    expect(result.imported?.updated).toBe(1);
    expect(importHealthConnectSleep).toHaveBeenCalledOnce();
    const items = vi.mocked(importHealthConnectSleep).mock.calls[0][0];
    expect(items).toHaveLength(1);
    expect(items[0].sleep_minutes).toBe(450);
  });

  it('reports sync_disabled instead of ok when the server has the toggle off', async () => {
    vi.mocked(readHealthConnectSleepAndHeartRate).mockResolvedValue({
      sleep: [{ startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 }],
      heartRate: [],
    });
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 0,
      skipped_existing_value: 0,
      skipped_no_entry: 1,
      sleep_sync_enabled: false,
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('sync_disabled');
  });
});
