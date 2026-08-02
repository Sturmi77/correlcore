/** Shared PII scrubbing for GlitchTip / Sentry events (M9 Sprint 2). */

const SENSITIVE_KEYS = new Set([
  'password',
  'hashed_password',
  'current_password',
  'new_password',
  'note',
  'note_enc',
  'mood_score',
  'energy',
  'stress',
  // ADR-0033 Art. 9 cycle SHD (parity with backend error_tracking scrubber).
  'cycle_day',
  'cycle_bleeding_level',
  // M8 Sprint 1 (#172): manual sleep is health data — keep parity with BE scrubber.
  'sleep_minutes',
  'sleep_quality',
  'symptoms',
  'symptom_intensity',
  'intensity',
  'email',
  'display_name',
  'authorization',
  'cookie',
  'access_token',
  'refresh_token',
  'token',
  'name_enc',
  'wrapped_dek',
  'encryption_key',
  'secret_key',
]);

const EMAIL_RE = /[^@\s]+@[^@\s]+\.[^@\s]+/g;
const REDACTED = '[Filtered]';

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/-/g, '_');
  if (SENSITIVE_KEYS.has(normalized)) return true;
  return ['password', 'token', 'note', 'email'].some((fragment) => normalized.includes(fragment));
}

function scrubString(value: string): string {
  return value.replace(EMAIL_RE, REDACTED);
}

export function scrubValue(key: string, value: unknown): unknown {
  if (isSensitiveKey(key)) return REDACTED;
  if (Array.isArray(value)) return value.map((item) => scrubValue(key, item));
  if (value && typeof value === 'object') return scrubMapping(value as Record<string, unknown>);
  if (typeof value === 'string') return scrubString(value);
  return value;
}

export function scrubMapping(data: Record<string, unknown>): Record<string, unknown> {
  const scrubbed: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data)) {
    scrubbed[key] = scrubValue(key, value);
  }
  return scrubbed;
}

type SentryEvent = {
  message?: string;
  request?: {
    data?: Record<string, unknown>;
    cookies?: Record<string, unknown>;
    headers?: Record<string, unknown>;
  };
  user?: Record<string, unknown>;
  extra?: Record<string, unknown>;
  contexts?: Record<string, unknown>;
  breadcrumbs?: {
    values?: Array<{
      data?: Record<string, unknown>;
      message?: string;
    }>;
  };
};

export function scrubSentryEvent<T extends SentryEvent>(event: T): T {
  if (event.request?.data) {
    event.request.data = scrubMapping(event.request.data);
  }
  if (event.request?.cookies) {
    event.request.cookies = Object.fromEntries(
      Object.keys(event.request.cookies).map((key) => [key, REDACTED])
    );
  }
  if (event.request?.headers) {
    event.request.headers = scrubMapping(event.request.headers);
  }
  if (event.user) {
    event.user = Object.fromEntries(
      Object.entries(event.user).map(([key, value]) => [
        key,
        key === 'email' || key === 'username' || key === 'ip_address' ? REDACTED : value,
      ])
    );
  }
  if (event.extra) {
    event.extra = scrubMapping(event.extra);
  }
  if (event.contexts) {
    event.contexts = scrubMapping(event.contexts);
  }
  if (event.breadcrumbs?.values) {
    for (const crumb of event.breadcrumbs.values) {
      if (crumb.data) crumb.data = scrubMapping(crumb.data);
      if (crumb.message) crumb.message = scrubString(crumb.message);
    }
  }
  if (event.message) {
    event.message = scrubString(event.message);
  }
  return event;
}
