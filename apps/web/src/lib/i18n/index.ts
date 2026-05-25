import { browser } from '$app/environment';
import { init, locale, register } from 'svelte-i18n';

const defaultLocale = 'de';
const supportedLocales = ['de', 'en'] as const;
const STORAGE_KEY = 'correlcore-locale';

export type AppLocale = (typeof supportedLocales)[number];

register('de', () => import('./locales/de.json'));
register('en', () => import('./locales/en.json'));

export function setupI18n(preferredLocale?: string) {
  const storedLocale = browser ? localStorage.getItem(STORAGE_KEY) : null;
  const resolvedLocale =
    preferredLocale ?? storedLocale ?? (browser ? navigator.language.split('-')[0] : defaultLocale);
  const finalLocale = supportedLocales.includes(resolvedLocale as AppLocale)
    ? (resolvedLocale as AppLocale)
    : defaultLocale;

  init({
    fallbackLocale: defaultLocale,
    initialLocale: finalLocale,
  });

  if (browser) {
    locale.set(finalLocale);
  }
}

export function setAppLocale(nextLocale: AppLocale): void {
  if (browser) {
    localStorage.setItem(STORAGE_KEY, nextLocale);
  }
  locale.set(nextLocale);
}
