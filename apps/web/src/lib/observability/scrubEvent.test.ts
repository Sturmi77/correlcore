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
          note: 'private journal',
        },
        cookies: { access_token: 'secret' },
        headers: { authorization: 'Bearer token', 'x-request-id': 'req-1' },
      },
      user: { email: 'alice@example.com', id: 'user-1' },
      extra: { symptoms: [{ slug: 'headache' }] },
    });

    expect(scrubbed.request?.data?.password).toBe('[Filtered]');
    expect(scrubbed.request?.data?.mood_score).toBe('[Filtered]');
    expect(scrubbed.request?.data?.note).toBe('[Filtered]');
    expect(scrubbed.request?.cookies?.access_token).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.authorization).toBe('[Filtered]');
    expect(scrubbed.request?.headers?.['x-request-id']).toBe('req-1');
    expect(scrubbed.user?.email).toBe('[Filtered]');
    expect(scrubbed.extra?.symptoms).toBe('[Filtered]');
    expect(scrubbed.message).not.toContain('alice@example.com');
  });

  it('keeps non-sensitive identifiers', () => {
    expect(scrubMapping({ user_id: '00000000-0000-4000-8000-000000000001' })).toEqual({
      user_id: '00000000-0000-4000-8000-000000000001',
    });
  });
});
