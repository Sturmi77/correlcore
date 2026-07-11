/** Client-side GlitchTip / Sentry initialisation (optional DSN). */

import * as Sentry from '@sentry/browser';
import { env } from '$env/dynamic/public';

import { scrubSentryEvent } from './scrubEvent';

let initialised = false;

export function initClientErrorTracking(): void {
  if (initialised || typeof window === 'undefined') return;

  const dsn = env.PUBLIC_GLITCHTIP_DSN?.trim();
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: env.PUBLIC_GLITCHTIP_ENVIRONMENT?.trim() || import.meta.env.MODE,
    beforeSend(event) {
      return scrubSentryEvent(event);
    },
    tracesSampleRate: 0,
  });

  initialised = true;
}

export function captureClientException(error: unknown): void {
  if (!initialised) return;
  Sentry.captureException(error);
}
