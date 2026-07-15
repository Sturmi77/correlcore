import { describe, expect, it } from 'vitest';
import { computeNoteSummaryShort, hasNote } from './noteSummary';

describe('noteSummary', () => {
  it('truncates long notes to 120 chars', () => {
    const summary = computeNoteSummaryShort('a'.repeat(200));
    expect(summary).not.toBeNull();
    expect(summary!.length).toBeLessThanOrEqual(120);
    expect(summary!.endsWith('…')).toBe(true);
  });

  it('detects note presence from body or summary', () => {
    expect(hasNote({ note: 'hello' })).toBe(true);
    expect(hasNote({ note_summary_short: 'preview' })).toBe(true);
    expect(hasNote({ note: null, note_summary_short: null })).toBe(false);
  });
});
