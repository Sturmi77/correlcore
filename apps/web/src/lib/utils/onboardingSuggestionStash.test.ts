import { afterEach, describe, expect, it } from 'vitest';
import {
  clearAllOnboardingSuggestionStashes,
  clearOnboardingSuggestionStash,
  hasOnboardingSuggestionStash,
  readOnboardingSuggestionStash,
  writeOnboardingSuggestionStash,
} from './onboardingSuggestionStash';

const suggestion = {
  slug: 'caffeine',
  name: 'Caffeine',
  category: 'consumption' as const,
  icon: null,
  color: null,
};

afterEach(() => {
  clearAllOnboardingSuggestionStashes();
});

describe('onboardingSuggestionStash', () => {
  it('rounds trips picks scoped by user id', () => {
    writeOnboardingSuggestionStash({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: true,
    });

    expect(hasOnboardingSuggestionStash('user-a')).toBe(true);
    expect(hasOnboardingSuggestionStash('user-b')).toBe(false);
    expect(readOnboardingSuggestionStash('user-a')).toEqual({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: true,
    });
    expect(readOnboardingSuggestionStash('user-b')).toBeNull();
  });

  it('treats toggle-only stashes as non-deferred for the gate helper', () => {
    writeOnboardingSuggestionStash({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: false,
    });
    expect(readOnboardingSuggestionStash('user-a')?.finalizeDeferred).toBe(false);
    expect(hasOnboardingSuggestionStash('user-a')).toBe(false);
  });

  it('clears one user without touching another', () => {
    writeOnboardingSuggestionStash({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: true,
    });
    writeOnboardingSuggestionStash({
      userId: 'user-b',
      suggestions: [{ ...suggestion, slug: 'sleep' }],
      finalizeDeferred: true,
    });

    clearOnboardingSuggestionStash('user-a');
    expect(hasOnboardingSuggestionStash('user-a')).toBe(false);
    expect(hasOnboardingSuggestionStash('user-b')).toBe(true);
  });

  it('clearAll drops every onboarding stash key', () => {
    writeOnboardingSuggestionStash({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: true,
    });
    writeOnboardingSuggestionStash({
      userId: 'user-b',
      suggestions: [suggestion],
      finalizeDeferred: false,
    });

    clearAllOnboardingSuggestionStashes();
    expect(hasOnboardingSuggestionStash('user-a')).toBe(false);
    expect(readOnboardingSuggestionStash('user-b')).toBeNull();
  });

  it('ignores corrupt payloads', () => {
    sessionStorage.setItem('cc_onboarding_suggestion_stash:user-a', '{not-json');
    expect(readOnboardingSuggestionStash('user-a')).toBeNull();
  });
});
