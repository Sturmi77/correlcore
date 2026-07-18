import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/api/platform', () => ({
  isCapacitorBuild: vi.fn(() => false),
}));

import { isCapacitorBuild } from '$lib/api/platform';
import { cleanupDevServiceWorker, registerProdServiceWorker } from './serviceWorker';

describe('serviceWorker helpers', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
  });

  it('cleans up registrations and caches in dev', async () => {
    vi.stubEnv('DEV', true);
    vi.stubEnv('PROD', false);

    const unregister = vi.fn().mockResolvedValue(true);
    const getRegistrations = vi.fn().mockResolvedValue([{ unregister }]);
    const deleteCache = vi.fn().mockResolvedValue(true);
    const keys = vi.fn().mockResolvedValue(['correlcore-app-v1']);

    vi.stubGlobal('navigator', { serviceWorker: { getRegistrations } });
    vi.stubGlobal('caches', { keys, delete: deleteCache });

    await cleanupDevServiceWorker();

    expect(getRegistrations).toHaveBeenCalled();
    expect(unregister).toHaveBeenCalled();
    expect(deleteCache).toHaveBeenCalledWith('correlcore-app-v1');
  });

  it('registers the service worker in production browser builds', async () => {
    vi.stubEnv('DEV', false);
    vi.stubEnv('PROD', true);

    const register = vi.fn().mockResolvedValue({});
    vi.stubGlobal('navigator', { serviceWorker: { register } });

    await registerProdServiceWorker();

    expect(register).toHaveBeenCalledWith('/service-worker.js', { type: 'classic' });
  });

  it('skips service worker registration in Capacitor production builds', async () => {
    vi.stubEnv('DEV', false);
    vi.stubEnv('PROD', true);
    vi.mocked(isCapacitorBuild).mockReturnValue(true);

    const register = vi.fn().mockResolvedValue({});
    vi.stubGlobal('navigator', { serviceWorker: { register } });

    await registerProdServiceWorker();

    expect(register).not.toHaveBeenCalled();
  });
});
