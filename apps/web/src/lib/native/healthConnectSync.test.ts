import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./healthConnect', () => ({
  readHealthConnectSleep: vi.fn(),
}));
vi.mock('$lib/api/healthConnect', () => ({
  importHealthConnectSleep: vi.fn(),
}));
vi.mock('$lib/offline/featureFlag', () => ({
  canUseOfflineSync: vi.fn(() => false),
}));
vi.mock('$lib/offline/syncOrchestrator', () => ({
  scheduleSync: vi.fn(),
}));
vi.mock('$lib/stores/entriesOffline', () => ({
  fillLocalSleepAfterHealthConnectImport: vi.fn(async () => 0),
}));
vi.mock('$lib/observability/errorTracking.client', () => ({
  captureClientException: vi.fn(),
}));

import { ApiError, NetworkError } from '$lib/api/client';
import { importHealthConnectSleep } from '$lib/api/healthConnect';
import type { ConsentListResponse } from '$lib/api/consents';
import { canUseOfflineSync } from '$lib/offline/featureFlag';
import { scheduleSync } from '$lib/offline/syncOrchestrator';
import { captureClientException } from '$lib/observability/errorTracking.client';
import { fillLocalSleepAfterHealthConnectImport } from '$lib/stores/entriesOffline';
import { readHealthConnectSleep } from './healthConnect';
import {
  _resetHealthConnectSyncForTests,
  aggregateSleepByDate,
  drainHealthConnectSyncForSessionChange,
  mapHealthConnectImportError,
  syncHealthConnectSleep,
} from './healthConnectSync';

const granted = {
  current: [{ consent_type: 'health_connect', granted: true }],
} as unknown as ConsentListResponse;
const revoked = {
  current: [{ consent_type: 'health_connect', granted: false }],
} as unknown as ConsentListResponse;

const range = { start: '2026-07-03T00:00:00Z', end: '2026-08-02T00:00:00Z' };

describe('aggregateSleepByDate', () => {
  it('merges overlapping sessions ending at the same instant instead of double-counting', () => {
    const map = aggregateSleepByDate([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 480 },
      { startTime: 'y', endTime: '2026-08-02T06:00:00Z', durationMinutes: 60 },
    ]);
    expect(map.size).toBe(1);
    expect([...map.values()][0]).toBe(480);
  });

  it('sums genuinely separate, non-overlapping sessions on the same wake-date', () => {
    const map = aggregateSleepByDate([
      { startTime: '2026-08-01T22:00:00Z', endTime: '2026-08-02T06:00:00Z', durationMinutes: 480 },
      { startTime: '2026-08-02T07:00:00Z', endTime: '2026-08-02T07:30:00Z', durationMinutes: 30 },
    ]);
    expect(map.size).toBe(1);
    expect([...map.values()][0]).toBe(510);
  });

  it('clamps a day total to 1440 minutes', () => {
    const wakeDay = new Date(2026, 7, 2);
    const end1 = new Date(wakeDay);
    end1.setHours(6, 0, 0, 0);
    const start1 = new Date(end1.getTime() - 720 * 60_000);
    const end2 = new Date(wakeDay);
    end2.setHours(22, 0, 0, 0);
    const start2 = new Date(end2.getTime() - 840 * 60_000);
    const map = aggregateSleepByDate([
      {
        startTime: start1.toISOString(),
        endTime: end1.toISOString(),
        durationMinutes: 720,
      },
      {
        startTime: start2.toISOString(),
        endTime: end2.toISOString(),
        durationMinutes: 840,
      },
    ]);
    expect(map.size).toBe(1);
    expect([...map.values()][0]).toBe(1440);
  });

  it('keeps sessions on different days separate', () => {
    const map = aggregateSleepByDate([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 400 },
      { startTime: 'y', endTime: '2026-08-04T06:00:00Z', durationMinutes: 420 },
    ]);
    expect(map.size).toBe(2);
  });
});

describe('mapHealthConnectImportError', () => {
  it('maps network and HTTP statuses', () => {
    expect(mapHealthConnectImportError(new NetworkError('/health-connect/import'))).toBe(
      'error_network'
    );
    expect(mapHealthConnectImportError(new ApiError(401, 'unauthorized', '/x'))).toBe(
      'error_unauthorized'
    );
    expect(mapHealthConnectImportError(new ApiError(403, 'forbidden', '/x'))).toBe(
      'error_forbidden'
    );
    expect(mapHealthConnectImportError(new ApiError(404, 'missing', '/x'))).toBe('error_not_found');
    expect(mapHealthConnectImportError(new ApiError(500, 'boom', '/x'))).toBe('error_server');
    expect(mapHealthConnectImportError(new ApiError(422, 'bad', '/x'))).toBe('error');
    expect(mapHealthConnectImportError(new Error('other'))).toBe('error');
  });
});

describe('syncHealthConnectSleep', () => {
  beforeEach(() => {
    _resetHealthConnectSyncForTests();
    vi.mocked(readHealthConnectSleep).mockReset();
    vi.mocked(importHealthConnectSleep).mockReset();
    vi.mocked(canUseOfflineSync).mockReset();
    vi.mocked(canUseOfflineSync).mockReturnValue(false);
    vi.mocked(scheduleSync).mockReset();
    vi.mocked(fillLocalSleepAfterHealthConnectImport).mockReset();
    vi.mocked(fillLocalSleepAfterHealthConnectImport).mockResolvedValue(0);
    vi.mocked(captureClientException).mockReset();
  });
  afterEach(() => {
    _resetHealthConnectSyncForTests();
    vi.clearAllMocks();
  });

  it('refuses without consent and never reads the bridge', async () => {
    const result = await syncHealthConnectSleep(revoked, range);
    expect(result.status).toBe('no_consent');
    expect(readHealthConnectSleep).not.toHaveBeenCalled();
  });

  it('reports unavailable when the bridge returns null', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue(null);
    const result = await syncHealthConnectSleep(granted, range);
    expect(result.status).toBe('unavailable');
    expect(importHealthConnectSleep).not.toHaveBeenCalled();
  });

  it('reports no_data when there are no sleep records', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([]);
    const result = await syncHealthConnectSleep(granted, range);
    expect(result.status).toBe('no_data');
    expect(importHealthConnectSleep).not.toHaveBeenCalled();
  });

  it('aggregates and imports sleep when records are present', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 1,
      skipped_existing_value: 0,
      skipped_no_entry: 0,
      sleep_sync_enabled: true,
      updated_entry_dates: ['2026-08-02'],
      skipped_existing_entry_dates: [],
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('ok');
    expect(result.imported?.updated).toBe(1);
    expect(importHealthConnectSleep).toHaveBeenCalledOnce();
    const items = vi.mocked(importHealthConnectSleep).mock.calls[0][0];
    expect(items).toHaveLength(1);
    expect(items[0].sleep_minutes).toBe(450);
    // Surfaces the touched wake-dates for the sync summary UI (#653 A2).
    expect(result.dates).toEqual([items[0].entry_date]);
    expect(fillLocalSleepAfterHealthConnectImport).toHaveBeenCalledOnce();
    expect(fillLocalSleepAfterHealthConnectImport).toHaveBeenCalledWith(
      [expect.objectContaining({ sleep_minutes: 450 })],
      { skippedExistingDates: [] }
    );
    expect(scheduleSync).not.toHaveBeenCalled();
  });

  it('reports sync_disabled instead of ok when the server has the toggle off', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 0,
      skipped_existing_value: 0,
      skipped_no_entry: 1,
      sleep_sync_enabled: false,
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('sync_disabled');
    expect(fillLocalSleepAfterHealthConnectImport).not.toHaveBeenCalled();
    expect(scheduleSync).not.toHaveBeenCalled();
  });

  it('reports no_matching_entries when sleep exists but no day entries', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 0,
      skipped_existing_value: 0,
      skipped_no_entry: 1,
      sleep_sync_enabled: true,
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('no_matching_entries');
    expect(fillLocalSleepAfterHealthConnectImport).not.toHaveBeenCalled();
  });

  it('reports already_up_to_date when every matched day already has sleep', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 0,
      skipped_existing_value: 1,
      skipped_no_entry: 0,
      sleep_sync_enabled: true,
      skipped_existing_entry_dates: ['2026-08-02'],
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('already_up_to_date');
    expect(fillLocalSleepAfterHealthConnectImport).toHaveBeenCalledOnce();
  });

  it('maps import ApiError to a specific status without throwing', async () => {
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockRejectedValue(
      new ApiError(404, 'Not Found', '/health-connect/import')
    );

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('error_not_found');
    expect(captureClientException).toHaveBeenCalledOnce();
  });

  it('schedules sync after Dexie reconcile when offline sync is enabled', async () => {
    vi.mocked(canUseOfflineSync).mockReturnValue(true);
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 1,
      skipped_existing_value: 0,
      skipped_no_entry: 0,
      sleep_sync_enabled: true,
      updated_entry_dates: ['2026-08-02'],
      skipped_existing_entry_dates: [],
    });
    vi.mocked(fillLocalSleepAfterHealthConnectImport).mockResolvedValue(1);

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('ok');
    expect(fillLocalSleepAfterHealthConnectImport).toHaveBeenCalledOnce();
    expect(scheduleSync).toHaveBeenCalledOnce();
  });

  it('reconciles Dexie when the server skipped dates that already had sleep (#640)', async () => {
    vi.mocked(canUseOfflineSync).mockReturnValue(true);
    vi.mocked(readHealthConnectSleep).mockResolvedValue([
      { startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 },
    ]);
    vi.mocked(importHealthConnectSleep).mockResolvedValue({
      updated: 0,
      skipped_existing_value: 1,
      skipped_no_entry: 0,
      sleep_sync_enabled: true,
      updated_entry_dates: [],
      skipped_existing_entry_dates: ['2026-08-02'],
    });

    const result = await syncHealthConnectSleep(granted, range);

    expect(result.status).toBe('already_up_to_date');
    expect(fillLocalSleepAfterHealthConnectImport).toHaveBeenCalledWith(
      [expect.objectContaining({ sleep_minutes: 450 })],
      { skippedExistingDates: ['2026-08-02'] }
    );
    expect(scheduleSync).toHaveBeenCalledOnce();
  });

  it('aborts import when the authenticated user changes during the native read', async () => {
    let currentId: string | null = 'user-a';
    type SleepRows = { startTime: string; endTime: string; durationMinutes: number }[];
    let releaseRead: (value: SleepRows) => void = () => {};
    const readGate = new Promise<SleepRows>((resolve) => {
      releaseRead = resolve;
    });
    vi.mocked(readHealthConnectSleep).mockReturnValue(readGate);

    const syncPromise = syncHealthConnectSleep(granted, range, {
      actorUserId: 'user-a',
      currentUserId: () => currentId,
    });

    // Account switch while Health Connect is still reading sessions.
    currentId = 'user-b';
    releaseRead([{ startTime: 'x', endTime: '2026-08-02T06:00:00Z', durationMinutes: 450 }]);

    const result = await syncPromise;
    expect(result.status).toBe('error_unauthorized');
    expect(importHealthConnectSleep).not.toHaveBeenCalled();
    expect(fillLocalSleepAfterHealthConnectImport).not.toHaveBeenCalled();
  });

  it('drains an in-flight Sync now before session credentials can change', async () => {
    type SleepRows = { startTime: string; endTime: string; durationMinutes: number }[];
    let releaseRead: (value: SleepRows) => void = () => {};
    const readGate = new Promise<SleepRows>((resolve) => {
      releaseRead = resolve;
    });
    vi.mocked(readHealthConnectSleep).mockReturnValue(readGate);

    const syncPromise = syncHealthConnectSleep(granted, range);
    let drained = false;
    const drainPromise = drainHealthConnectSyncForSessionChange().then(() => {
      drained = true;
    });

    expect(drained).toBe(false);
    releaseRead([]);
    await syncPromise;
    await drainPromise;
    expect(drained).toBe(true);
  });
});
