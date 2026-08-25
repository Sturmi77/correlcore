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
    expect(homeSource).toContain('showLandingPreview');
    expect(homeSource).not.toContain('Pre-Alpha');
  });

  it('exposes login and register CTAs; APK stays in the Android section (#735 I4)', () => {
    expect(landingSource).toContain('data-testid="landing-cta-login"');
    expect(landingSource).toContain('href="/auth/login"');
    expect(landingSource).toContain('data-testid="landing-cta-register"');
    expect(landingSource).toContain('href="/auth/register"');
    expect(landingSource).not.toContain('data-testid="landing-cta-apk"');
    expect(landingSource).toContain('data-testid="landing-android-download"');
    expect(landingSource).toContain('ANDROID_RELEASES_URL');
  });

  it('shows the daily check-in as the hero product shot (#735 I2)', () => {
    expect(landingSource).toContain('LandingCheckinMock');
    expect(landingSource).toContain('data-testid="landing-paths"');
    expect(landingSource).toContain('landing-path-try');
    expect(landingSource).toContain('landing-path-host');
    expect(landingSource).toContain('landing-faq-');
  });

  it('links trust claims to backing documents (#735 I5)', () => {
    expect(landingSource).toContain('data-testid={`landing-trust-${item.key}`}');
    expect(landingSource).toContain("href: '/privacy'");
    expect(landingSource).toContain('SECURITY_URL');
    expect(landingSource).toContain('LICENSE_URL');
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
