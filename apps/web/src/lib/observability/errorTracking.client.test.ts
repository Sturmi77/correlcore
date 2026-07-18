import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const sentryMocks = vi.hoisted(() => ({
  init: vi.fn(),
  setTag: vi.fn(),
  captureException: vi.fn(),
}));

vi.mock('@sentry/browser', () => ({
  init: sentryMocks.init,
  setTag: sentryMocks.setTag,
  captureException: sentryMocks.captureException,
}));

vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_GLITCHTIP_DSN: '',
    PUBLIC_GLITCHTIP_ENVIRONMENT: '',
  },
}));

vi.mock('$lib/api/platform', () => ({
  isCapacitorBuild: vi.fn(() => false),
}));

import { env } from '$env/dynamic/public';
import { isCapacitorBuild } from '$lib/api/platform';
import {
  _resetClientErrorTrackingForTests,
  captureClientException,
  initClientErrorTracking,
} from './errorTracking.client';

describe('initClientErrorTracking', () => {
  beforeEach(() => {
    _resetClientErrorTrackingForTests();
    sentryMocks.init.mockClear();
    sentryMocks.setTag.mockClear();
    sentryMocks.captureException.mockClear();
    (env as { PUBLIC_GLITCHTIP_DSN: string }).PUBLIC_GLITCHTIP_DSN = '';
    (env as { PUBLIC_GLITCHTIP_ENVIRONMENT: string }).PUBLIC_GLITCHTIP_ENVIRONMENT = '';
    vi.mocked(isCapacitorBuild).mockReturnValue(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('skips Sentry when DSN is unset', () => {
    vi.stubGlobal('window', {});
    initClientErrorTracking();
    expect(sentryMocks.init).not.toHaveBeenCalled();
  });

  it('initialises Sentry and tags Capacitor runtime when DSN is set', () => {
    vi.stubGlobal('window', {});
    (env as { PUBLIC_GLITCHTIP_DSN: string }).PUBLIC_GLITCHTIP_DSN = 'https://key@errors.example/1';
    (env as { PUBLIC_GLITCHTIP_ENVIRONMENT: string }).PUBLIC_GLITCHTIP_ENVIRONMENT = 'android';
    vi.mocked(isCapacitorBuild).mockReturnValue(true);

    initClientErrorTracking();

    expect(sentryMocks.init).toHaveBeenCalledOnce();
    expect(sentryMocks.init.mock.calls[0]?.[0]).toMatchObject({
      dsn: 'https://key@errors.example/1',
      environment: 'android',
      tracesSampleRate: 0,
    });
    expect(sentryMocks.setTag).toHaveBeenCalledWith('runtime', 'capacitor');
  });

  it('captureClientException is a no-op until initialised', () => {
    captureClientException(new Error('boom'));
    expect(sentryMocks.captureException).not.toHaveBeenCalled();
  });

  it('captureClientException forwards after init', () => {
    vi.stubGlobal('window', {});
    (env as { PUBLIC_GLITCHTIP_DSN: string }).PUBLIC_GLITCHTIP_DSN = 'https://key@errors.example/1';
    initClientErrorTracking();

    const err = new Error('boom');
    captureClientException(err);
    expect(sentryMocks.captureException).toHaveBeenCalledWith(err);
  });
});
