/**
 * Default tag color mirrors `--color-primary` per theme in `app.css`.
 * Persisted as hex because tag colors are stored independently of runtime theme.
 */
export const TAG_DEFAULT_COLOR_DARK = '#7c6af5';
export const TAG_DEFAULT_COLOR_LIGHT = '#6356d9';

/** Returns the theme-appropriate primary hex for new tags and missing-color fallbacks. */
export function defaultTagColorForCurrentTheme(): string {
  if (typeof document === 'undefined') return TAG_DEFAULT_COLOR_DARK;
  const theme = document.documentElement.getAttribute('data-theme');
  return theme === 'light' ? TAG_DEFAULT_COLOR_LIGHT : TAG_DEFAULT_COLOR_DARK;
}
