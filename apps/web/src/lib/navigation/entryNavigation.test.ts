import { describe, expect, it } from 'vitest';
import { prefersEntrySheet, resolveEntryPath } from './entryNavigation';
import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';

describe('entryNavigation', () => {
  it('prefers the sheet below the desktop shell breakpoint', () => {
    expect(prefersEntrySheet(DESKTOP_SHELL_BREAKPOINT_PX - 1)).toBe(true);
    expect(prefersEntrySheet(DESKTOP_SHELL_BREAKPOINT_PX)).toBe(false);
  });

  it('resolves mobile and desktop entry paths', () => {
    expect(resolveEntryPath('2026-05-15', 390)).toBe('/?openEntry=1&date=2026-05-15');
    expect(resolveEntryPath('2026-05-15', 1280)).toBe('/entries/new?date=2026-05-15');
  });
});
