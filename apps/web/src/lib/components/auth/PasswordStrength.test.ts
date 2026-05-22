/**
 * Tests for the password-strength evaluator (Issue #40).
 *
 * Mirrors backend rules: min 8 chars, at least one letter, at least one digit.
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
  });

  it('flags letters-only as not meeting requirements', () => {
    expect(evaluatePassword('abcdefgh').meetsRequirements).toBe(false);
  });

  it('flags digits-only as not meeting requirements', () => {
    expect(evaluatePassword('12345678').meetsRequirements).toBe(false);
  });

  it('accepts the minimal compliant password', () => {
    const s = evaluatePassword('abcd1234');
    expect(s.meetsRequirements).toBe(true);
    expect(s.score).toBeGreaterThanOrEqual(2);
  });

  it('rewards length and symbols', () => {
    const weak = evaluatePassword('abcd1234'); // 8 chars, ok
    const longer = evaluatePassword('abcdefgh1234'); // 12 chars
    const strong = evaluatePassword('abcdefgh1234!'); // 13 chars + symbol
    expect(longer.score).toBeGreaterThanOrEqual(weak.score);
    expect(strong.score).toBeGreaterThanOrEqual(longer.score);
    expect(strong.score).toBe(4);
  });
});
