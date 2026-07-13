import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanupDevServiceWorker, registerProdServiceWorker } from './serviceWorker';

describe('serviceWorker helpers', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
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

  it('registers the service worker in production', async () => {
    vi.stubEnv('DEV', false);
    vi.stubEnv('PROD', true);

    const register = vi.fn().mockResolvedValue({});
    vi.stubGlobal('navigator', { serviceWorker: { register } });

    await registerProdServiceWorker();

    expect(register).toHaveBeenCalledWith('/service-worker.js', { type: 'module' });
  });
});
