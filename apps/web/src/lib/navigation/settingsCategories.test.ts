import { describe, expect, it } from 'vitest';
import { SETTINGS_CATEGORIES, isSettingsCategoryActive } from './settingsCategories';

describe('settingsCategories', () => {
  it('lists the four hub categories with stable routes', () => {
    expect(SETTINGS_CATEGORIES.map((c) => c.href)).toEqual([
      '/settings/data',
      '/settings/analysis',
      '/settings/privacy',
      '/settings/appearance',
    ]);
  });

  it('marks the category route as active (trailing slash ok)', () => {
    expect(isSettingsCategoryActive('/settings/data', '/settings/data')).toBe(true);
    expect(isSettingsCategoryActive('/settings/data/', '/settings/data')).toBe(true);
    expect(isSettingsCategoryActive('/settings/tags', '/settings/data')).toBe(false);
    expect(isSettingsCategoryActive('/settings/analysis', '/settings/data')).toBe(false);
  });
});
