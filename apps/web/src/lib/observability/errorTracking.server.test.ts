import { beforeEach, describe, expect, it, vi } from 'vitest';

const sentryMocks = vi.hoisted(() => ({
  init: vi.fn(),
  captureException: vi.fn(),
}));

vi.mock('@sentry/node', () => ({
  init: sentryMocks.init,
  captureException: sentryMocks.captureException,
}));

vi.mock('$env/dynamic/private', () => ({
  env: {
    GLITCHTIP_DSN: '',
    GLITCHTIP_ENVIRONMENT: '',
    APP_ENV: 'test',
  },
}));

vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_GLITCHTIP_DSN: '',
    PUBLIC_GLITCHTIP_ENVIRONMENT: '',
  },
}));

import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import {
  _resetServerErrorTrackingForTests,
  captureServerException,
  initServerErrorTracking,
} from './errorTracking.server';

describe('initServerErrorTracking', () => {
  beforeEach(() => {
    _resetServerErrorTrackingForTests();
    sentryMocks.init.mockClear();
    sentryMocks.captureException.mockClear();
    privateEnv.GLITCHTIP_DSN = '';
    privateEnv.GLITCHTIP_ENVIRONMENT = '';
    privateEnv.APP_ENV = 'test';
    publicEnv.PUBLIC_GLITCHTIP_DSN = '';
    publicEnv.PUBLIC_GLITCHTIP_ENVIRONMENT = '';
  });

  it('skips Sentry when DSN is unset', () => {
    initServerErrorTracking();
    expect(sentryMocks.init).not.toHaveBeenCalled();
  });

  it('keeps v10 restrictive data collection when DSN is set', () => {
    privateEnv.GLITCHTIP_DSN = 'https://key@errors.example/1';
    privateEnv.GLITCHTIP_ENVIRONMENT = 'production';

    initServerErrorTracking();

    expect(sentryMocks.init).toHaveBeenCalledOnce();
    expect(sentryMocks.init.mock.calls[0]?.[0]).toMatchObject({
      dsn: 'https://key@errors.example/1',
      environment: 'production',
      tracesSampleRate: 0,
      dataCollection: {
        userInfo: false,
        cookies: false,
        httpBodies: [],
        databaseQueryData: false,
        queues: false,
        httpHeaders: {
          request: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
          response: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
        },
      },
    });
  });

  it('captureServerException is a no-op until initialised', () => {
    captureServerException(new Error('boom'));
    expect(sentryMocks.captureException).not.toHaveBeenCalled();
  });

  it('captureServerException forwards after init', () => {
    privateEnv.GLITCHTIP_DSN = 'https://key@errors.example/1';
    initServerErrorTracking();

    const err = new Error('boom');
    captureServerException(err);
    expect(sentryMocks.captureException).toHaveBeenCalledWith(err);
  });
});
