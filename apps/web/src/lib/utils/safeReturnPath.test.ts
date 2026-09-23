import { describe, expect, it } from 'vitest';
import { safeInternalReturnPath } from './safeReturnPath';

describe('safeInternalReturnPath', () => {
  it('preserves an internal report path and its selected signal', () => {
    expect(safeInternalReturnPath('/insights/report?signal=a%2Fb')).toBe(
      '/insights/report?signal=a%2Fb'
    );
  });

  it.each([
    'https://evil.example/steal',
    '//evil.example/steal',
    '/\\evil.example/steal',
    '/auth/login?next=/insights/report',
    '/insights/report\n//evil.example',
  ])('rejects unsafe or recursive return target %s', (target) => {
    expect(safeInternalReturnPath(target)).toBe('/');
  });
});
