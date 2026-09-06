/**
 * Settings category routes (#694 / #702).
 *
 * Real sub-routes (not client tabs) so deep links, back, and bookmarks work.
 */

export type SettingsCategoryKey = 'data' | 'analysis' | 'privacy' | 'appearance';

export interface SettingsCategory {
  href: `/settings/${SettingsCategoryKey}`;
  key: SettingsCategoryKey;
  testId: `settings-cat-${SettingsCategoryKey}`;
}

export const SETTINGS_CATEGORIES: readonly SettingsCategory[] = [
  { href: '/settings/data', key: 'data', testId: 'settings-cat-data' },
  { href: '/settings/analysis', key: 'analysis', testId: 'settings-cat-analysis' },
  { href: '/settings/privacy', key: 'privacy', testId: 'settings-cat-privacy' },
  { href: '/settings/appearance', key: 'appearance', testId: 'settings-cat-appearance' },
] as const;

export function isSettingsCategoryActive(
  pathname: string,
  href: SettingsCategory['href']
): boolean {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  return normalized === href;
}
