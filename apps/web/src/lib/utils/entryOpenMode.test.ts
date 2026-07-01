import { afterEach, describe, expect, it } from 'vitest';
import { getEntryOpenMode, setEntryOpenMode } from './entryOpenMode';

describe('entryOpenMode', () => {
  afterEach(() => {
    localStorage.removeItem('cc_entry_open_mode');
  });

  it('defaults to full mode', () => {
    expect(getEntryOpenMode()).toBe('full');
  });

  it('persists quick mode', () => {
    setEntryOpenMode('quick');
    expect(getEntryOpenMode()).toBe('quick');
  });
});
