import { describe, expect, it } from 'vitest';
import { stripLegacyInsightStatementTails } from './stripLegacyInsightStatementTails';

describe('stripLegacyInsightStatementTails', () => {
  it('returns empty for nullish', () => {
    expect(stripLegacyInsightStatementTails(null)).toBe('');
    expect(stripLegacyInsightStatementTails(undefined)).toBe('');
  });

  it('strips a known diagnosis tail', () => {
    const raw =
      'Mood tends to be higher when energy is higher. This is a data pattern, not a diagnosis.';
    expect(stripLegacyInsightStatementTails(raw)).toBe(
      'Mood tends to be higher when energy is higher.'
    );
  });

  it('leaves descriptive statements unchanged', () => {
    const raw = 'Mood tends to be higher when energy is higher.';
    expect(stripLegacyInsightStatementTails(raw)).toBe(raw);
  });
});
