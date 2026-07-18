import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('./platform', () => ({
  isCapacitorBuild: vi.fn(() => true),
}));

import { isCapacitorBuild } from './platform';
import {
  _resetApiBaseForTests,
  capacitorNeedsApiBaseConfig,
  ensureCapacitorApiBaseConfigured,
  getApiBase,
  getApiBaseInputForDisplay,
  isRelativeApiBase,
  setRuntimeApiBase,
  validateAbsoluteApiBase,
} from './apiBase';

describe('apiBase helpers', () => {
  afterEach(() => {
    _resetApiBaseForTests();
    localStorage.clear();
    vi.mocked(isCapacitorBuild).mockReturnValue(true);
    vi.unstubAllEnvs();
  });

  it('detects relative vs absolute API bases', () => {
    expect(isRelativeApiBase('/api/v1')).toBe(true);
    expect(isRelativeApiBase('https://host.example/api/v1')).toBe(false);
  });

  it('validates absolute API bases ending with /api/v1', () => {
    expect(validateAbsoluteApiBase('https://host.example/api/v1')).toEqual({
      ok: true,
      normalized: 'https://host.example/api/v1',
    });
    expect(validateAbsoluteApiBase('https://host.example/api/v1/')).toEqual({
      ok: true,
      normalized: 'https://host.example/api/v1',
    });
    expect(validateAbsoluteApiBase('')).toEqual({ ok: false, reason: 'empty' });
    expect(validateAbsoluteApiBase('/api/v1')).toEqual({ ok: false, reason: 'invalid' });
    expect(validateAbsoluteApiBase('https://host.example/api')).toEqual({
      ok: false,
      reason: 'invalid',
    });
  });

  it('requires an absolute URL on Capacitor when the default is relative', () => {
    expect(getApiBase()).toBe('/api/v1');
    expect(capacitorNeedsApiBaseConfig()).toBe(true);
    expect(getApiBaseInputForDisplay()).toBe('');

    expect(ensureCapacitorApiBaseConfigured('')).toEqual({
      ok: false,
      errorKey: 'auth.login.error_api_base_required',
    });

    expect(ensureCapacitorApiBaseConfigured('https://host.example/api/v1')).toEqual({
      ok: true,
    });
    expect(getApiBase()).toBe('https://host.example/api/v1');
  });

  it('rejects invalid override input', () => {
    expect(ensureCapacitorApiBaseConfigured('not-a-url')).toEqual({
      ok: false,
      errorKey: 'settings.app.api_base_invalid',
    });
  });

  it('accepts empty input when an absolute override is already stored', () => {
    setRuntimeApiBase('https://already.set/api/v1');
    expect(ensureCapacitorApiBaseConfigured('')).toEqual({ ok: true });
  });

  it('is a no-op ensure on browser builds', () => {
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
    expect(ensureCapacitorApiBaseConfigured('')).toEqual({ ok: true });
    expect(capacitorNeedsApiBaseConfig()).toBe(false);
  });
});
