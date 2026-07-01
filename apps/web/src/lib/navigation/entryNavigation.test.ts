import { describe, expect, it } from 'vitest';
import { prefersEntrySheet, resolveEntryPath } from './entryNavigation';

describe('entryNavigation', () => {
  it('always prefers the global entry sheet', () => {
    expect(prefersEntrySheet(390)).toBe(true);
    expect(prefersEntrySheet(1280)).toBe(true);
  });

  it('resolves every viewport to the open-entry home path', () => {
    expect(resolveEntryPath('2026-05-15', 390)).toBe('/?openEntry=1&date=2026-05-15');
    expect(resolveEntryPath('2026-05-15', 1280)).toBe('/?openEntry=1&date=2026-05-15');
  });
});
