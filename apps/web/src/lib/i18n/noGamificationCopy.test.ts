import { describe, expect, it } from 'vitest';

import de from './locales/de.json';
import en from './locales/en.json';

function collectStrings(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(collectStrings);
  if (value && typeof value === 'object') {
    return Object.values(value).flatMap(collectStrings);
  }
  return [];
}

describe('no-gamification UI copy', () => {
  it('does not expose streak or reward framing in locale strings', () => {
    const forbidden = /\b(streak|reward|badge|fire)\b|don't break/i;
    const strings = [...collectStrings(en), ...collectStrings(de)];

    expect(strings.filter((copy) => forbidden.test(copy))).toEqual([]);
  });
});
