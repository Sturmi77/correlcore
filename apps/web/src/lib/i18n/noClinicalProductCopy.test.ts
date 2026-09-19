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

describe('no clinical product-framing UI copy', () => {
  it('does not expose burnout or clinical-inventory product claims in locale strings', () => {
    // Affirmative product framing only. Negated diagnosis disclaimers stay allowed.
    // See docs/features/arbeitsmuster-vokabular.md (Phase 9 / #930 G3).
    const forbidden = /\bburnout\b|\bMBI\b|\bCBI\b|burnout[- ]prevention|Burnout-Prävention/i;
    const strings = [...collectStrings(en), ...collectStrings(de)];

    expect(strings.filter((copy) => forbidden.test(copy))).toEqual([]);
  });
});
