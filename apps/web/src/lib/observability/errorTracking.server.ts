/** Server-side GlitchTip / Sentry initialisation for adapter-node. */

import * as Sentry from '@sentry/node';
import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

import { scrubSentryEvent } from './scrubEvent';

let initialised = false;

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
  });

  initialised = true;
}

export function captureServerException(error: unknown): void {
  if (!initialised) return;
  Sentry.captureException(error);
}
