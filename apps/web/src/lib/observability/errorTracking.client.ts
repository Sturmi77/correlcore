/** Client-side GlitchTip / Sentry initialisation (optional DSN). */

import * as Sentry from '@sentry/browser';
import { env } from '$env/dynamic/public';

import { isCapacitorBuild } from '$lib/api/platform';
import { scrubSentryEvent } from './scrubEvent';

let initialised = false;

export function initClientErrorTracking(): void {
  if (initialised || typeof window === 'undefined') return;

  const dsn = env.PUBLIC_GLITCHTIP_DSN?.trim();
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: env.PUBLIC_GLITCHTIP_ENVIRONMENT?.trim() || import.meta.env.MODE,
    beforeSend(event, _hint) {
      scrubSentryEvent(event as Parameters<typeof scrubSentryEvent>[0]);
      return event;
    },
    tracesSampleRate: 0,
  });

  Sentry.setTag('runtime', isCapacitorBuild() ? 'capacitor' : 'web');

  initialised = true;
}

export function captureClientException(error: unknown): void {
  if (!initialised) return;
  Sentry.captureException(error);
}

/** Test-only: allow re-init after env stubs change. */
export function _resetClientErrorTrackingForTests(): void {
  initialised = false;
}
