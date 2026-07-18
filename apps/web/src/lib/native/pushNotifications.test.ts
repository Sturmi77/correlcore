import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/platform', () => ({
  isCapacitorBuild: vi.fn(() => true),
}));

vi.mock('$lib/api/devices', () => ({
  registerPushToken: vi.fn(),
  unregisterPushToken: vi.fn(),
}));

const requestPermissions = vi.fn();
const register = vi.fn();
const addListener = vi.fn().mockResolvedValue({ remove: vi.fn() });

vi.mock('@capacitor/push-notifications', () => ({
  PushNotifications: {
    requestPermissions,
    register,
    addListener,
  },
}));

import { isCapacitorBuild } from '$lib/api/platform';
import {
  _resetPushNotificationsForTests,
  enablePushNotifications,
  isPushAvailable,
} from './pushNotifications';

describe('pushNotifications', () => {
  beforeEach(() => {
    _resetPushNotificationsForTests();
    vi.mocked(isCapacitorBuild).mockReturnValue(true);
    requestPermissions.mockReset().mockResolvedValue({ receive: 'granted' });
    register.mockReset().mockResolvedValue(undefined);
    addListener.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubCapacitor(plugins: Record<string, unknown> = {}) {
    vi.stubGlobal('window', {
      Capacitor: {
        isNativePlatform: () => true,
        Plugins: plugins,
      },
    });
  }

  it('isPushAvailable is false when PushAvailability plugin is missing', async () => {
    stubCapacitor({});
    await expect(isPushAvailable()).resolves.toBe(false);
  });

  it('isPushAvailable reflects BuildConfig.FCM_ENABLED from the native plugin', async () => {
    stubCapacitor({
      PushAvailability: {
        isAvailable: vi.fn().mockResolvedValue({ available: true }),
      },
    });
    await expect(isPushAvailable()).resolves.toBe(true);
  });

  it('skips register when FCM is not wired (sideload APK)', async () => {
    stubCapacitor({
      PushAvailability: {
        isAvailable: vi.fn().mockResolvedValue({ available: false }),
      },
    });

    await enablePushNotifications();

    expect(requestPermissions).not.toHaveBeenCalled();
    expect(register).not.toHaveBeenCalled();
  });

  it('requests permission and registers when FCM is available', async () => {
    stubCapacitor({
      PushAvailability: {
        isAvailable: vi.fn().mockResolvedValue({ available: true }),
      },
    });

    await enablePushNotifications();

    expect(requestPermissions).toHaveBeenCalledOnce();
    expect(register).toHaveBeenCalledOnce();
  });

  it('no-ops outside native Capacitor', async () => {
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
    stubCapacitor({
      PushAvailability: {
        isAvailable: vi.fn().mockResolvedValue({ available: true }),
      },
    });

    await enablePushNotifications();

    expect(requestPermissions).not.toHaveBeenCalled();
    expect(register).not.toHaveBeenCalled();
  });
});
