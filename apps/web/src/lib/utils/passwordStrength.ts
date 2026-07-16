/**
 * Password strength helper.
 *
 * Mirrors backend ``app.core.password_policy``:
 * - min length 12
 * - at least one letter
 * - at least one digit
 *
 * The score is advisory UX only; the backend re-validates every request.
 */

export const MIN_PASSWORD_LENGTH = 12;

export interface Strength {
  score: 0 | 1 | 2 | 3 | 4;
  meetsRequirements: boolean;
  rules: { ok: boolean; key: string }[];
}

export function evaluatePassword(password: string): Strength {
  const len = password.length;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);
  const longish = len >= 16;

  const rules = [
    { ok: len >= MIN_PASSWORD_LENGTH, key: 'rule_min_length' },
    { ok: hasLetter, key: 'rule_letter' },
    { ok: hasDigit, key: 'rule_digit' },
  ];

  const meetsRequirements = rules.every((r) => r.ok);

  let score: Strength['score'] = 0;
  if (len > 0) score = 1;
  if (meetsRequirements) score = 2;
  if (meetsRequirements && (hasSymbol || longish)) score = 3;
  if (meetsRequirements && hasSymbol && longish) score = 4;

  return { score, meetsRequirements, rules };
}
