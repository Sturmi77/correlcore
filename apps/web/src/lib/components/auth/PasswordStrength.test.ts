/**
 * Tests for the password-strength evaluator.
 *
 * Mirrors backend rules: min 12 chars, at least one letter, at least one digit.
 * Score is purely advisory UX.
 */

import { describe, expect, it } from 'vitest';
import { evaluatePassword } from '$lib/utils/passwordStrength';

describe('evaluatePassword', () => {
  it('reports score 0 + not-meeting for empty input', () => {
    const s = evaluatePassword('');
    expect(s.score).toBe(0);
    expect(s.meetsRequirements).toBe(false);
  });

  it('flags short passwords as not meeting requirements', () => {
    expect(evaluatePassword('abc1').meetsRequirements).toBe(false);
    expect(evaluatePassword('abcd1234').meetsRequirements).toBe(false);
  });

  it('flags letters-only as not meeting requirements', () => {
    expect(evaluatePassword('abcdefghijkl').meetsRequirements).toBe(false);
  });

  it('flags digits-only as not meeting requirements', () => {
    expect(evaluatePassword('123456789012').meetsRequirements).toBe(false);
  });

  it('accepts the minimal compliant password', () => {
    const s = evaluatePassword('abcd1234wxyz');
    expect(s.meetsRequirements).toBe(true);
    expect(s.score).toBeGreaterThanOrEqual(2);
  });

  it('rewards length and symbols', () => {
    const ok = evaluatePassword('abcd1234wxyz'); // 12 chars
    const longer = evaluatePassword('abcdefghijklmn12'); // 16 chars
    const strong = evaluatePassword('abcdefghijklmn12!'); // 17 chars + symbol
    expect(longer.score).toBeGreaterThanOrEqual(ok.score);
    expect(strong.score).toBeGreaterThanOrEqual(longer.score);
    expect(strong.score).toBe(4);
  });
});
