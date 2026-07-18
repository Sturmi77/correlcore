import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(resolve('src/routes/+page.svelte'), 'utf8');
const layoutSource = readFileSync(resolve('src/routes/+layout.svelte'), 'utf8');
const homeDailyBriefSource = readFileSync(
  resolve('src/lib/components/home/HomeDailyBrief.svelte'),
  'utf8'
);
const firstWeekBannerSource = readFileSync(
  resolve('src/lib/components/home/FirstWeekInsightBanner.svelte'),
  'utf8'
);
const globalEntrySheetSource = readFileSync(
  resolve('src/lib/components/entries/GlobalEntrySheet.svelte'),
  'utf8'
);
const entryLaunchButtonSource = readFileSync(
  resolve('src/lib/components/entries/EntryLaunchButton.svelte'),
  'utf8'
);

describe('/ home screen ownership contract', () => {
  it('keeps advanced insight journey UI off the daily touch point', () => {
    expect(source).not.toContain('InsightJourneyBanner');
    expect(source).not.toContain('InsightPhaseMilestoneCard');
    expect(source).not.toContain('shouldShowMaturityMilestone');
  });

  it('shows the maturity expectation sheet before first-entry tag onboarding', () => {
    expect(source).toContain('MaturityExpectationSheet');
    expect(source).toContain('shouldShowMaturityExpectationIntro');
    expect(source).toContain('onboarding_maturity_intro_seen');
    // Entry sheet opens only after the intro was seen.
    expect(source).toContain('userPreferences.onboarding_maturity_intro_seen');
  });

  it('does not duplicate app navigation or session controls on Home', () => {
    expect(source).not.toContain('home-links');
    expect(source).not.toContain('home-logout');
    expect(source).not.toContain('handleLogout');
  });

  it('uses the global entry sheet store instead of a local sheet instance', () => {
    expect(layoutSource).toContain('GlobalEntrySheet');
    expect(source).toContain('openEntrySheet');
    expect(source).not.toContain('<EntrySheet');
  });

  it('exposes weekly analysis bridge links from the daily brief', () => {
    expect(homeDailyBriefSource).toContain('href="/insights"');
    expect(homeDailyBriefSource).toContain('href="/trends"');
    expect(homeDailyBriefSource).toContain('data-testid="home-weekly-bridge"');
    expect(homeDailyBriefSource).toContain('data-testid="home-brief-milestone-progress"');
    expect(firstWeekBannerSource).not.toContain('href="/insights"');
  });

  it('opens entry inline from launch buttons without routing to /entries/new', () => {
    expect(entryLaunchButtonSource).toContain('openEntrySheet');
    expect(entryLaunchButtonSource).not.toContain('/entries/new');
  });

  it('uses the shared Button primitive for entry actions', () => {
    const todayContextSource = readFileSync(
      resolve('src/lib/components/home/HomeTodayContext.svelte'),
      'utf8'
    );
    expect(source).toContain('$lib/components/common/Button.svelte');
    expect(source).toContain('data-testid="home-cta"');
    expect(source).toContain('{#if !todayEntry}');
    expect(source).not.toContain('HomeSparkline');
    expect(todayContextSource).toContain('data-testid="home-today-action"');
    expect(todayContextSource).toContain('{#if !loading && todayEntry}');
  });

  it('surfaces weekday and work-context patterns without adding a separate dashboard zone', () => {
    expect(source).toContain('HomeWeekdayOverview');
    expect(source).toContain('workContextSummary={dashboardSummary?.work_context_summary ?? []}');
    expect(globalEntrySheetSource).toContain('{workContextTypical}');
  });

  it('defers the PWA install banner until after the first entry or retro onboarding', () => {
    expect(source).toContain('data-testid="pwa-install-banner"');
    expect(source).toContain('(dashboardSummary?.entry_count ?? 0) >= 1');
    expect(source).toContain('userPreferences?.onboarding_retro_completed');
  });
});
