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

  it('clears one user without touching another', () => {
    writeOnboardingSuggestionStash({
      userId: 'user-a',
      suggestions: [suggestion],
      finalizeDeferred: false,
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
    expect(hasOnboardingSuggestionStash('user-b')).toBe(false);
  });

  it('ignores corrupt payloads', () => {
    sessionStorage.setItem('cc_onboarding_suggestion_stash:user-a', '{not-json');
    expect(readOnboardingSuggestionStash('user-a')).toBeNull();
  });
});
