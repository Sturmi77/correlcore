import { describe, expect, it } from 'vitest';
import { localizedCatalogName } from './localizedCatalogName';

describe('localizedCatalogName', () => {
  const t = (key: string) => (key === 'tag.default.walk' ? 'Walk' : key);

  it('uses the i18n catalogue label for default tags', () => {
    expect(localizedCatalogName('walk', true, 'Spaziergang', t)).toBe('Walk');
  });

  it('keeps the stored name for custom tags', () => {
    expect(localizedCatalogName('walk', false, 'Evening walk', t)).toBe('Evening walk');
  });

  it('falls back to the stored name when the key is missing', () => {
    expect(localizedCatalogName('custom-slug', true, 'Stored', t)).toBe('Stored');
  });
});
