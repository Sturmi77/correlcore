import { browser } from '$app/environment';
import { init, register } from 'svelte-i18n';

const defaultLocale = 'de';

register('de', () => import('./locales/de.json'));
register('en', () => import('./locales/en.json'));

export function setupI18n(locale?: string) {
  const resolvedLocale = locale ?? (browser ? navigator.language.split('-')[0] : defaultLocale);
  const supported = ['de', 'en'];
  const finalLocale = supported.includes(resolvedLocale) ? resolvedLocale : defaultLocale;

  init({
    fallbackLocale: defaultLocale,
    initialLocale: finalLocale,
  });
}
