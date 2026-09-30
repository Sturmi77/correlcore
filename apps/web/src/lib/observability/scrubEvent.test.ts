import { describe, expect, it } from 'vitest';

import { scrubMapping, scrubSentryEvent } from './scrubEvent';

describe('scrubSentryEvent', () => {
  it('redacts health data, credentials, and email addresses', () => {
    const scrubbed = scrubSentryEvent({
      message: 'failed for alice@example.com',
      request: {
        data: {
          password: 'CorrectHorse123!',
          mood_score: 3,
          cycle_day: 14,
          cycle_bleeding_level: 'light',
          sleep_minutes: 420,
          sleep_quality: 4,
          note: 'private journal',
        },
        cookies: { access_token: 'secret' },
        headers: { authorization: 'Bearer token', 'x-request-id': 'req-1' },
      },
      user: { email: 'alice@example.com', id: 'user-1' },
      extra: { symptoms: [{ slug: 'headache' }] },
    });

    const data = scrubbed.request?.data as Record<string, unknown>;
    expect(data.password).toBe('[Filtered]');
    expect(data.mood_score).toBe('[Filtered]');
    expect(data.cycle_day).toBe('[Filtered]');
    expect(data.cycle_bleeding_level).toBe('[Filtered]');
    expect(data.sleep_minutes).toBe('[Filtered]');
    expect(data.sleep_quality).toBe('[Filtered]');
    expect(data.note).toBe('[Filtered]');
    expect(scrubbed.request?.cookies?.access_token).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.authorization).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['x-request-id']).toBe('req-1');
    expect(scrubbed.user?.email).toBe('[Filtered]');
    expect(scrubbed.extra?.symptoms).toBe('[Filtered]');
    expect(scrubbed.message).not.toContain('alice@example.com');
  });

  it('drops raw request bodies and proxy client IPs', () => {
    const scrubbed = scrubSentryEvent({
      request: {
        data: JSON.stringify({
          password: 'hunter2',
          note: 'chest pain after poor sleep',
        }),
        headers: {
          'x-forwarded-for': '203.0.113.50',
          'x-real-ip': '203.0.113.50',
          'x-request-id': 'req-1',
        },
      },
      user: { ip_address: '203.0.113.50', id: 'user-1' },
    });

    expect(scrubbed.request?.data).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['x-forwarded-for']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['x-real-ip']).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['x-request-id']).toBe('req-1');
    expect(scrubbed.user?.ip_address).toBe('[Filtered]');
    expect(scrubbed.user?.id).toBe('user-1');
  });

  it('keeps non-sensitive identifiers', () => {
    expect(scrubMapping({ user_id: '00000000-0000-4000-8000-000000000001' })).toEqual({
      user_id: '00000000-0000-4000-8000-000000000001',
    });
  });
});
