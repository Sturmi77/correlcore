import { describe, expect, it } from 'vitest';
import {
  buildOpenEntryPath,
  entryDateFromSearchParams,
  entryWorkspacePath,
  isOpenEntryRequested,
  OPEN_ENTRY_HOME_PATH,
  OPEN_ENTRY_QUERY,
} from './openEntry';

describe('openEntry navigation', () => {
  it('detects the openEntry query flag', () => {
    expect(isOpenEntryRequested(new URLSearchParams('openEntry=1'))).toBe(true);
    expect(isOpenEntryRequested(new URLSearchParams('openEntry=0'))).toBe(false);
    expect(isOpenEntryRequested(new URLSearchParams())).toBe(false);
  });

  it('exposes the canonical home path', () => {
    expect(OPEN_ENTRY_HOME_PATH).toBe(`/?${OPEN_ENTRY_QUERY}=1`);
  });

  it('builds open-entry paths with optional date', () => {
    expect(buildOpenEntryPath()).toBe('/?openEntry=1');
    expect(buildOpenEntryPath('2026-05-15')).toBe('/?openEntry=1&date=2026-05-15');
  });

  it('parses entry dates from search params', () => {
    expect(entryDateFromSearchParams(new URLSearchParams('date=2026-05-15'))).toBe('2026-05-15');
    expect(entryDateFromSearchParams(new URLSearchParams('date=bad'))).toBeNull();
  });

  it('builds desktop workspace paths', () => {
    expect(entryWorkspacePath()).toBe('/entries/new');
    expect(entryWorkspacePath('2026-05-15')).toBe('/entries/new?date=2026-05-15');
  });
});
