import { describe, expect, it } from 'vitest';
import {
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
});
