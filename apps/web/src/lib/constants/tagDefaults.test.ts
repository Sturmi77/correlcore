import { afterEach, describe, expect, it } from 'vitest';
import {
  TAG_DEFAULT_COLOR_DARK,
  TAG_DEFAULT_COLOR_LIGHT,
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
