import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/platform', () => ({
  isCapacitorBuild: vi.fn(() => true),
}));

import { isCapacitorBuild } from '$lib/api/platform';
import type { ConsentListResponse } from '$lib/api/consents';
import {
  checkHealthConnectPermissions,
  isHealthConnectAvailable,
  isHealthConnectBridgePresent,
  readHealthConnectSleepAndHeartRate,
  requestHealthConnectPermissions,
} from './healthConnect';

const grantedConsents = {
  current: [{ consent_type: 'health_connect', granted: true }],
} as unknown as ConsentListResponse;

const revokedConsents = {
  current: [{ consent_type: 'health_connect', granted: false }],
} as unknown as ConsentListResponse;

describe('healthConnect bridge', () => {
  const isAvailable = vi.fn();
  const checkPermissions = vi.fn();
  const requestPermissions = vi.fn();
  const readSleepAndHeartRate = vi.fn();

  beforeEach(() => {
    isAvailable.mockReset().mockResolvedValue({ available: true, status: 3 });
    checkPermissions.mockReset().mockResolvedValue({ granted: true, available: true });
    requestPermissions.mockReset().mockResolvedValue({ granted: true, available: true });
    readSleepAndHeartRate.mockReset().mockResolvedValue({ sleep: [], heartRate: [] });
    vi.mocked(isCapacitorBuild).mockReturnValue(true);
    vi.stubGlobal('window', {
      Capacitor: {
        Plugins: {
          HealthConnect: {
            isAvailable,
            checkHealthPermissions: checkPermissions,
            requestHealthPermissions: requestPermissions,
            readSleepAndHeartRate,
          },
        },
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reports the bridge present on a capacitor build with the plugin', () => {
    expect(isHealthConnectBridgePresent()).toBe(true);
  });

  it('reports no bridge on a browser build', () => {
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
    expect(isHealthConnectBridgePresent()).toBe(false);
  });

  it('refuses to request permissions without server consent', async () => {
    const state = await requestHealthConnectPermissions(revokedConsents);
    expect(state).toEqual({ granted: false, available: false });
    expect(requestPermissions).not.toHaveBeenCalled();
  });

  it('requests permissions when consent is granted', async () => {
    const state = await requestHealthConnectPermissions(grantedConsents);
    expect(requestPermissions).toHaveBeenCalledOnce();
    expect(state.granted).toBe(true);
  });

  it('returns null on read without consent (never touches the plugin)', async () => {
    const result = await readHealthConnectSleepAndHeartRate(revokedConsents, {
      start: '2026-08-01T00:00:00Z',
      end: '2026-08-02T00:00:00Z',
    });
    expect(result).toBeNull();
    expect(readSleepAndHeartRate).not.toHaveBeenCalled();
  });

  it('reads records when consent is granted', async () => {
    readSleepAndHeartRate.mockResolvedValue({
      sleep: [{ startTime: 'a', endTime: 'b', durationMinutes: 420 }],
      heartRate: [],
    });
    const result = await readHealthConnectSleepAndHeartRate(grantedConsents, {
      start: '2026-08-01T00:00:00Z',
      end: '2026-08-02T00:00:00Z',
    });
    expect(readSleepAndHeartRate).toHaveBeenCalledOnce();
    expect(result?.sleep[0].durationMinutes).toBe(420);
  });

  it('degrades gracefully when the native plugin is absent', async () => {
    vi.stubGlobal('window', { Capacitor: { Plugins: {} } });
    expect(await isHealthConnectAvailable()).toEqual({ available: false });
    expect(await checkHealthConnectPermissions()).toEqual({ granted: false, available: false });
  });
});
