import { describe, expect, it } from 'vitest';
import de from './locales/de.json';
import en from './locales/en.json';

function flattenKeys(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    flattenKeys(child, prefix ? `${prefix}.${key}` : key)
  );
}

describe('locale completeness', () => {
  it('keeps DE and EN keys in sync', () => {
    const deKeys = flattenKeys(de).sort();
    const enKeys = flattenKeys(en).sort();

    expect(deKeys).toEqual(enKeys);
  });
});
