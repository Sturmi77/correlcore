import type { TagCategory } from '$lib/api/tags';

/**
 * Default tag color mirrors `--color-primary` per theme in `app.css`.
 * Persisted as hex because tag colors are stored independently of runtime theme.
 */
export const TAG_DEFAULT_COLOR_DARK = '#7c6af5';
export const TAG_DEFAULT_COLOR_LIGHT = '#6356d9';

/** True when the runtime theme is light (attribute set explicitly). */
function isLightTheme(): boolean {
  if (typeof document === 'undefined') return false;
  return document.documentElement.getAttribute('data-theme') === 'light';
}

/** Returns the theme-appropriate primary hex for new tags and missing-color fallbacks. */
export function defaultTagColorForCurrentTheme(): string {
  return isLightTheme() ? TAG_DEFAULT_COLOR_LIGHT : TAG_DEFAULT_COLOR_DARK;
}

/**
 * Per-category ("group") color, the suggested colour when a new tag is created
 * (#672 — category iconography + colour carry per-item identity). One distinct
 * hue per category, mirrored per theme: the `dark` variant is lighter/brighter
 * for legibility on the dark surface, the `light` variant darker for contrast on
 * the light surface — the same lightness pattern as the primary default, so each
 * reads correctly under `--color-text-inverse` chip text. `other` falls back to
 * the primary default.
 */
export const CATEGORY_COLORS: Record<TagCategory, { dark: string; light: string }> = {
  sport: { dark: '#fb923c', light: '#c2410c' },
  social: { dark: '#60a5fa', light: '#2563eb' },
  work: { dark: '#818cf8', light: '#4f46e5' },
  leisure: { dark: '#f472b6', light: '#be185d' },
  consumption: { dark: '#4ade80', light: '#15803d' },
  health: { dark: '#f87171', light: '#b91c1c' },
  cycle: { dark: '#2dd4bf', light: '#0f766e' },
  other: { dark: TAG_DEFAULT_COLOR_DARK, light: TAG_DEFAULT_COLOR_LIGHT },
};

/** Suggested hex for a tag in `category`, resolved for the current theme. */
export function categoryColorForCurrentTheme(category: TagCategory): string {
  const pair = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.other;
  return isLightTheme() ? pair.light : pair.dark;
}
