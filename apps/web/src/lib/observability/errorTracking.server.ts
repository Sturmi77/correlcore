/** Server-side GlitchTip / Sentry initialisation for adapter-node. */

import * as Sentry from '@sentry/node';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

import { scrubSentryEvent } from './scrubEvent';

let initialised = false;

/**
 * @sentry/node 11 collects request bodies, cookies, and client IPs when
 * `dataCollection` is omitted. Keep the restrictive v10 profile: journal
 * payloads and proxy client IPs must not be attached to error events.
 */
const restrictiveDataCollection = {
  userInfo: false,
  cookies: false,
  httpHeaders: {
    request: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
    response: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
  },
  httpBodies: [] as (
    'incomingRequest' | 'outgoingRequest' | 'incomingResponse' | 'outgoingResponse'
  )[],
  urlQueryParams: { deny: ['forwarded', '-ip', 'remote-', 'via', '-user'] },
  genAI: { inputs: false, outputs: false },
  databaseQueryData: false,
  queues: false,
  graphQL: { document: false, variables: false },
};

export function initServerErrorTracking(): void {
  if (initialised) return;

  const dsn = (privateEnv.GLITCHTIP_DSN ?? publicEnv.PUBLIC_GLITCHTIP_DSN ?? '').trim();
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment:
      privateEnv.GLITCHTIP_ENVIRONMENT?.trim() ||
      publicEnv.PUBLIC_GLITCHTIP_ENVIRONMENT?.trim() ||
      privateEnv.APP_ENV ||
      'production',
    beforeSend(event, _hint) {
      scrubSentryEvent(event as Parameters<typeof scrubSentryEvent>[0]);
      return event;
    },
    tracesSampleRate: 0,
    dataCollection: restrictiveDataCollection,
  });

  initialised = true;
}

/** Test-only: allow re-init after env stubs change. */
export function _resetServerErrorTrackingForTests(): void {
  initialised = false;
}

export function captureServerException(error: unknown): void {
  if (!initialised) return;
  Sentry.captureException(error);
}
