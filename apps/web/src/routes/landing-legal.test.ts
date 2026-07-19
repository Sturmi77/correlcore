import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const homeSource = readFileSync(resolve('src/routes/+page.svelte'), 'utf8');
const landingSource = readFileSync(
  resolve('src/lib/components/landing/LandingPage.svelte'),
  'utf8'
);
const legalFooterSource = readFileSync(
  resolve('src/lib/components/common/LegalFooter.svelte'),
  'utf8'
);
const impressumSource = readFileSync(resolve('src/routes/impressum/+page.svelte'), 'utf8');
const privacySource = readFileSync(resolve('src/routes/privacy/+page.svelte'), 'utf8');
const authLayoutSource = readFileSync(resolve('src/routes/auth/+layout.svelte'), 'utf8');

describe('M10 marketing landing and legal pages', () => {
  it('uses the marketing landing component for anonymous home', () => {
    expect(homeSource).toContain('LandingPage');
    expect(homeSource).not.toContain('Pre-Alpha');
  });

  it('exposes login, APK download, and register CTAs on the landing page', () => {
    expect(landingSource).toContain('data-testid="landing-cta-login"');
    expect(landingSource).toContain('href="/auth/login"');
    expect(landingSource).toContain('data-testid="landing-cta-apk"');
    expect(landingSource).toContain('ANDROID_RELEASES_URL');
    expect(landingSource).toContain('data-testid="landing-cta-register"');
    expect(landingSource).toContain('href="/auth/register"');
  });

  it('links privacy and impressum from the legal footer', () => {
    expect(landingSource).toContain('LegalFooter');
    expect(legalFooterSource).toContain('data-testid="legal-footer-privacy"');
    expect(legalFooterSource).toContain('data-testid="legal-footer-impressum"');
    expect(privacySource).toContain('LegalFooter');
    expect(impressumSource).toContain('LegalFooter');
  });

  it('provides impressum sections for AT/DE legal notice', () => {
    expect(impressumSource).toContain('data-testid={`impressum-section-${key}`}');
    expect(impressumSource).toContain("'operator'");
    expect(impressumSource).toContain("'dispute'");
  });

  it('links privacy and impressum from auth layout footer', () => {
    expect(authLayoutSource).toContain('data-testid="auth-footer-privacy"');
    expect(authLayoutSource).toContain('data-testid="auth-footer-impressum"');
  });
});
