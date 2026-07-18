import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const logoSource = readFileSync(resolve('src/lib/components/common/CorrelCoreLogo.svelte'), 'utf8');
const splashSource = readFileSync(
  resolve('src/lib/components/common/CorrelCoreSplash.svelte'),
  'utf8'
);
const layoutSource = readFileSync(resolve('src/routes/+layout.svelte'), 'utf8');
const authLayoutSource = readFileSync(resolve('src/routes/auth/+layout.svelte'), 'utf8');
const settingsSource = readFileSync(resolve('src/routes/settings/+page.svelte'), 'utf8');
const homeSource = readFileSync(resolve('src/routes/+page.svelte'), 'utf8');
const appNavSource = readFileSync(resolve('src/lib/components/common/AppNav.svelte'), 'utf8');
const appCssSource = readFileSync(resolve('src/app.css'), 'utf8');
const manifestSource = readFileSync(resolve('static/manifest.webmanifest'), 'utf8');

describe('Claude Design brand mark wiring', () => {
  it('uses theme heatmap tokens for the logo mark', () => {
    expect(logoSource).toContain('var(--color-heatmap-1)');
    expect(logoSource).toContain('var(--color-heatmap-4)');
    expect(logoSource).toContain('var(--color-primary)');
    expect(logoSource).not.toContain('A20 20 0 0 1 44 24');
  });

  it('ships a CSS-driven boot splash with reduced-motion support', () => {
    expect(splashSource).toContain('cc-tile-in');
    expect(splashSource).toContain('prefers-reduced-motion');
    expect(splashSource).toContain('var(--color-heatmap-1)');
  });

  it('gates boot behind CorrelCoreSplash with a minimum display window', () => {
    expect(layoutSource).toContain('CorrelCoreSplash');
    expect(layoutSource).toContain('showBrandSplash');
    expect(layoutSource).toContain('SPLASH_MIN_MS');
    expect(layoutSource).not.toContain('class="auth-splash"');
  });

  it('uses CorrelCoreLogo in the auth chrome', () => {
    expect(authLayoutSource).toContain('CorrelCoreLogo');
    expect(authLayoutSource).not.toContain('A20 20 0 0 1 44 24');
  });

  it('places the brand mark in Settings footer, not on authenticated Home', () => {
    expect(settingsSource).toContain('CorrelCoreLogo');
    expect(settingsSource).toContain('settings__version');
    expect(homeSource).not.toContain('CorrelCoreLogo');
  });

  it('anchors a desktop-only brand mark in the AppNav rail', () => {
    expect(appNavSource).toContain('CorrelCoreLogo');
    expect(appNavSource).toContain('app-nav__brand');
    expect(appCssSource).toContain('.app-nav__brand');
    expect(appCssSource).toMatch(/\.app-nav__brand\s*\{\s*display:\s*none;/);
  });

  it('uses the theme-aware brand mark for the Home nav destination', () => {
    expect(appNavSource).toContain('app-nav-home-mark');
    expect(appNavSource).toContain('BRAND_MARK_SM');
    expect(appNavSource).not.toContain("import House from 'lucide-svelte/icons/house'");
    expect(appCssSource).toContain('.app-nav__home-mark');
  });

  it('points the web manifest at the new PNG/SVG icons', () => {
    expect(manifestSource).toContain('/icons/correlcore-app-icon.png');
    expect(manifestSource).toContain('/icons/correlcore-icon-dark-bg.png');
    expect(manifestSource).toContain('/icons/icon.svg');
  });
});
