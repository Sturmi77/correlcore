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

  it('does not duplicate Home navigation in primary route headers', () => {
    expect(routeSources.insights).not.toContain('insights-page__top');
    expect(routeSources.trends).not.toContain('trends__top');
    expect(routeSources.settings).not.toContain('settings__top');
    expect(routeSources.insights).not.toContain('href="/">{$_(\'nav.home\')}');
    expect(routeSources.trends).not.toContain('href="/">{$_(\'nav.home\')}');
    expect(routeSources.settings).not.toContain('href="/">{$_(\'nav.home\')}');
  });

  it('does not duplicate Insights navigation from Settings', () => {
    expect(routeSources.settings).not.toContain('href="/insights"');
    expect(routeSources.settings).not.toContain('settings.analysis.insights');
  });

  it('keeps route-level theme controls out of non-settings screens', () => {
    expect(routeSources.insights).not.toContain('ThemeToggle');
    expect(routeSources.trends).not.toContain('ThemeToggle');
    expect(routeSources.tagSettings).not.toContain('ThemeToggle');
  });
});
