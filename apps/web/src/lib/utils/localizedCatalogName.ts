/**
 * Display name for a curated default tag. Custom tags keep the stored name.
 * svelte-i18n returns the key itself when a translation is missing.
 */
export function localizedCatalogName(
  slug: string,
  isDefault: boolean,
  fallback: string,
  t: (key: string) => string
): string {
  if (!isDefault) return fallback;
  const key = `tag.default.${slug}`;
  const translated = t(key);
  return translated === key ? fallback : translated;
}
