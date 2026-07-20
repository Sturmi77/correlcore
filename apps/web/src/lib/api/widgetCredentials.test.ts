import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./platform', () => ({
  isCapacitorBuild: vi.fn(() => true),
}));

vi.mock('./apiBase', () => ({
  getApiBase: vi.fn(() => 'https://api.example/api/v1'),
}));

import { isCapacitorBuild } from './platform';
import {
  mirrorWidgetCredentials,
  readWidgetCredentials,
  remirrorWidgetApiBase,
} from './widgetCredentials';

describe('widgetCredentials', () => {
  const set = vi.fn();
  const clear = vi.fn();
  const get = vi.fn();

  beforeEach(() => {
    set.mockReset().mockResolvedValue(undefined);
    clear.mockReset().mockResolvedValue(undefined);
    get.mockReset().mockResolvedValue({});
    vi.mocked(isCapacitorBuild).mockReturnValue(true);
    vi.stubGlobal('window', {
      Capacitor: {
        Plugins: {
          WidgetCredentials: { set, clear, get },
        },
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('mirrors access + refresh + api base to the native plugin', async () => {
    await mirrorWidgetCredentials('access-1', 'refresh-1');
    expect(set).toHaveBeenCalledWith({
      accessToken: 'access-1',
      refreshToken: 'refresh-1',
      apiBase: 'https://api.example/api/v1',
    });
  });

  it('clears when access or refresh is missing', async () => {
    await mirrorWidgetCredentials('access-1', null);
    expect(clear).toHaveBeenCalledOnce();
    expect(set).not.toHaveBeenCalled();
  });

  it('remirrorWidgetApiBase forwards both tokens', async () => {
    await remirrorWidgetApiBase('access-2', 'refresh-2');
    expect(set).toHaveBeenCalledWith({
      accessToken: 'access-2',
      refreshToken: 'refresh-2',
      apiBase: 'https://api.example/api/v1',
    });
  });

  it('no-ops outside Capacitor builds', async () => {
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
    await mirrorWidgetCredentials('a', 'r');
    expect(set).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
  });

  it('readWidgetCredentials returns mirrored tokens', async () => {
    get.mockResolvedValueOnce({
      accessToken: 'aw',
      refreshToken: 'rw',
      apiBase: 'https://api.example/api/v1',
    });
    await expect(readWidgetCredentials()).resolves.toEqual({
      accessToken: 'aw',
      refreshToken: 'rw',
      apiBase: 'https://api.example/api/v1',
    });
  });
});
