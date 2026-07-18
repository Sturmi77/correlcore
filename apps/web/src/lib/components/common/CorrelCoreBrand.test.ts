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

  it('gates i18n/auth loading behind CorrelCoreSplash', () => {
    expect(layoutSource).toContain('CorrelCoreSplash');
    expect(layoutSource).toContain("label={$_('a11y.loading')}");
    expect(layoutSource).not.toContain('class="auth-splash"');
  });

  it('uses CorrelCoreLogo in the auth chrome', () => {
    expect(authLayoutSource).toContain('CorrelCoreLogo');
    expect(authLayoutSource).not.toContain('A20 20 0 0 1 44 24');
  });

  it('points the web manifest at the new PNG/SVG icons', () => {
    expect(manifestSource).toContain('/icons/correlcore-app-icon.png');
    expect(manifestSource).toContain('/icons/correlcore-icon-dark-bg.png');
    expect(manifestSource).toContain('/icons/icon.svg');
  });
});
