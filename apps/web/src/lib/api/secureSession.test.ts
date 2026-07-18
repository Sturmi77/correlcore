import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./platform', () => ({
  isCapacitorBuild: () => true,
}));

vi.mock('./apiBase', () => ({
  getApiBase: () => 'https://api.example/api/v1',
}));

describe('secureSession', () => {
  const plugin = {
    set: vi.fn(async () => undefined),
    get: vi.fn(async () => ({})),
    clear: vi.fn(async () => undefined),
  };

  beforeEach(() => {
    vi.resetModules();
    plugin.set.mockClear();
    plugin.get.mockClear();
    plugin.clear.mockClear();
    vi.stubGlobal('window', {
      Capacitor: { Plugins: { SecureSession: plugin } },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persistSecureSession writes when rememberMe is true', async () => {
    const { persistSecureSession } = await import('./secureSession');
    await persistSecureSession({
      accessToken: 'a',
      refreshToken: 'r',
      rememberMe: true,
    });
    expect(plugin.set).toHaveBeenCalledWith({
      accessToken: 'a',
      refreshToken: 'r',
      apiBase: 'https://api.example/api/v1',
      rememberMe: true,
    });
  });

  it('persistSecureSession clears when rememberMe is false', async () => {
    const { persistSecureSession } = await import('./secureSession');
    await persistSecureSession({
      refreshToken: 'r',
      rememberMe: false,
    });
    expect(plugin.clear).toHaveBeenCalled();
    expect(plugin.set).not.toHaveBeenCalled();
  });

  it('restoreSecureSession returns null without refresh', async () => {
    plugin.get.mockResolvedValueOnce({});
    const { restoreSecureSession } = await import('./secureSession');
    await expect(restoreSecureSession()).resolves.toBeNull();
  });

  it('restoreSecureSession maps plugin payload', async () => {
    plugin.get.mockResolvedValueOnce({
      accessToken: 'a2',
      refreshToken: 'r2',
      apiBase: 'https://host/api/v1',
      rememberMe: true,
    });
    const { restoreSecureSession } = await import('./secureSession');
    await expect(restoreSecureSession()).resolves.toEqual({
      accessToken: 'a2',
      refreshToken: 'r2',
      apiBase: 'https://host/api/v1',
      rememberMe: true,
    });
  });
});
