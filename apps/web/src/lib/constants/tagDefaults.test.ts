import { afterEach, describe, expect, it } from 'vitest';
import { TAG_CATEGORIES } from '$lib/api/tags';
import {
  CATEGORY_COLORS,
  TAG_DEFAULT_COLOR_DARK,
  TAG_DEFAULT_COLOR_LIGHT,
  categoryColorForCurrentTheme,
  defaultTagColorForCurrentTheme,
} from './tagDefaults';

describe('defaultTagColorForCurrentTheme', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme');
  });

  it('returns dark primary when theme is dark', () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    expect(defaultTagColorForCurrentTheme()).toBe(TAG_DEFAULT_COLOR_DARK);
  });

  it('returns light primary when theme is light', () => {
    document.documentElement.setAttribute('data-theme', 'light');
    expect(defaultTagColorForCurrentTheme()).toBe(TAG_DEFAULT_COLOR_LIGHT);
  });

  it('defaults to dark when theme attribute is missing', () => {
    expect(defaultTagColorForCurrentTheme()).toBe(TAG_DEFAULT_COLOR_DARK);
  });
});

describe('categoryColorForCurrentTheme', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme');
  });

  it('has a distinct colour pair for every category', () => {
    for (const category of TAG_CATEGORIES) {
      expect(CATEGORY_COLORS[category]).toBeDefined();
      expect(CATEGORY_COLORS[category].dark).toMatch(/^#[0-9a-f]{6}$/);
      expect(CATEGORY_COLORS[category].light).toMatch(/^#[0-9a-f]{6}$/);
    }
    const darkHues = TAG_CATEGORIES.map((c) => CATEGORY_COLORS[c].dark);
    expect(new Set(darkHues).size).toBe(TAG_CATEGORIES.length);
  });

  it('returns the theme-appropriate category colour', () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    expect(categoryColorForCurrentTheme('sport')).toBe(CATEGORY_COLORS.sport.dark);
    document.documentElement.setAttribute('data-theme', 'light');
    expect(categoryColorForCurrentTheme('sport')).toBe(CATEGORY_COLORS.sport.light);
  });

  it('falls back to the primary default for the "other" category', () => {
    document.documentElement.setAttribute('data-theme', 'dark');
    expect(categoryColorForCurrentTheme('other')).toBe(TAG_DEFAULT_COLOR_DARK);
    document.documentElement.setAttribute('data-theme', 'light');
    expect(categoryColorForCurrentTheme('other')).toBe(TAG_DEFAULT_COLOR_LIGHT);
  });
});
