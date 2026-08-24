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

  it('gives drill-down screens one visible ScreenHeader with a back affordance (#703)', () => {
    // Stage 1: the three hand-rolled `__top` bars are folded into ScreenHeader's
    // shared `back` prop instead of raw btn anchors + duplicate headings.
    for (const source of [routeSources.dayEntries, routeSources.dev, routeSources.admin]) {
      expect(source).toContain('<ScreenHeader');
      expect(source).toContain('back={{');
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
