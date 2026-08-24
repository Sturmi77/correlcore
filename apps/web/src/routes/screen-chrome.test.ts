import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const routeSources = {
  insights: readFileSync(resolve('src/routes/insights/+page.svelte'), 'utf8'),
  trends: readFileSync(resolve('src/routes/trends/+page.svelte'), 'utf8'),
  settings: readFileSync(resolve('src/routes/settings/+page.svelte'), 'utf8'),
  tagSettings: readFileSync(resolve('src/routes/settings/tags/+page.svelte'), 'utf8'),
  appSettings: readFileSync(resolve('src/routes/settings/app/+page.svelte'), 'utf8'),
  symptomSettings: readFileSync(resolve('src/routes/settings/symptoms/+page.svelte'), 'utf8'),
  analysisSettings: readFileSync(resolve('src/routes/settings/analysis/+page.svelte'), 'utf8'),
  appearanceSettings: readFileSync(resolve('src/routes/settings/appearance/+page.svelte'), 'utf8'),
  dataSettings: readFileSync(resolve('src/routes/settings/data/+page.svelte'), 'utf8'),
  homeSettings: readFileSync(resolve('src/routes/settings/home/+page.svelte'), 'utf8'),
  privacySettings: readFileSync(resolve('src/routes/settings/privacy/+page.svelte'), 'utf8'),
  insightsDigest: readFileSync(resolve('src/routes/insights/digest/+page.svelte'), 'utf8'),
  insightsHistory: readFileSync(resolve('src/routes/insights/history/+page.svelte'), 'utf8'),
  healthConnect: readFileSync(resolve('src/routes/health-connect/+page.svelte'), 'utf8'),
  dayEntries: readFileSync(resolve('src/routes/entries/day/[date]/+page.svelte'), 'utf8'),
  dev: readFileSync(resolve('src/routes/dev/+page.svelte'), 'utf8'),
  admin: readFileSync(resolve('src/routes/admin/+page.svelte'), 'utf8'),
  onboarding: readFileSync(resolve('src/routes/onboarding/+page.svelte'), 'utf8'),
  onboardingProfile: readFileSync(resolve('src/routes/onboarding/profile/+page.svelte'), 'utf8'),
  onboardingRetro: readFileSync(resolve('src/routes/onboarding/retro/+page.svelte'), 'utf8'),
};

describe('screen chrome contract', () => {
  it('uses ScreenHeader for primary and secondary screen headings', () => {
    for (const source of Object.values(routeSources)) {
      expect(source).toContain('$lib/components/common/ScreenHeader.svelte');
      expect(source).toContain('<ScreenHeader');
    }
  });

  it('uses screen-stack on settings sub-routes', () => {
    expect(routeSources.tagSettings).toContain('screen-stack');
    expect(routeSources.appSettings).toContain('screen-stack');
    expect(routeSources.symptomSettings).toContain('screen-stack');
  });

  it('uses visuallyHidden ScreenHeader on onboarding routes', () => {
    for (const source of [
      routeSources.onboarding,
      routeSources.onboardingProfile,
      routeSources.onboardingRetro,
    ]) {
      expect(source).toContain('visuallyHidden');
    }
  });

  it('gives every drill-down screen one shared ScreenHeader back affordance (#703)', () => {
    // One back pattern everywhere: ScreenHeader's `back` prop (a left-aligned
    // ghost link), not per-screen `__top` bars or `slot="actions"` back buttons.
    const drillDowns = [
      routeSources.dayEntries,
      routeSources.dev,
      routeSources.admin,
      routeSources.analysisSettings,
      routeSources.appSettings,
      routeSources.appearanceSettings,
      routeSources.dataSettings,
      routeSources.homeSettings,
      routeSources.privacySettings,
      routeSources.symptomSettings,
      routeSources.tagSettings,
      routeSources.insightsDigest,
      routeSources.insightsHistory,
      routeSources.healthConnect,
    ];
    for (const source of drillDowns) {
      expect(source).toContain('<ScreenHeader');
      expect(source).toContain('back={{');
      // No screen re-implements back as a header action button.
      expect(source).not.toContain('slot="actions" href="/settings"');
      expect(source).not.toContain('slot="actions" href="/insights"');
    }
    // The drill-down header is now visible (not the a11y-only hidden variant).
    expect(routeSources.dayEntries).not.toContain('visuallyHidden');
  });

  it('does not hand-roll custom __top header bars', () => {
    expect(routeSources.insights).not.toContain('insights-page__top');
    expect(routeSources.trends).not.toContain('trends__top');
    expect(routeSources.settings).not.toContain('settings__top');
    expect(routeSources.dayEntries).not.toContain('day-entries__top');
    expect(routeSources.dev).not.toContain('dev__top');
    expect(routeSources.admin).not.toContain('admin__top');
    expect(routeSources.insights).not.toContain('href="/">{$_(\'nav.home\')}');
    expect(routeSources.trends).not.toContain('href="/">{$_(\'nav.home\')}');
    expect(routeSources.settings).not.toContain('href="/">{$_(\'nav.home\')}');
  });

  it('does not duplicate Insights navigation from Settings', () => {
    expect(routeSources.settings).not.toContain('href="/insights"');
    expect(routeSources.settings).not.toContain('settings.analysis.insights');
  });

  it('keeps route-level theme controls out of non-appearance screens', () => {
    // ThemeToggle policy (#703): the toggle lives in Appearance settings; ad-hoc
    // copies in drill-down/utility screens were removed.
    expect(routeSources.insights).not.toContain('ThemeToggle');
    expect(routeSources.trends).not.toContain('ThemeToggle');
    expect(routeSources.tagSettings).not.toContain('ThemeToggle');
    expect(routeSources.dayEntries).not.toContain('ThemeToggle');
    expect(routeSources.dev).not.toContain('ThemeToggle');
  });
});
