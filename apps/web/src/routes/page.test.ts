import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(resolve('src/routes/+page.svelte'), 'utf8');
const homeDailyBriefSource = readFileSync(
  resolve('src/lib/components/home/HomeDailyBrief.svelte'),
  'utf8'
);
const firstWeekBannerSource = readFileSync(
  resolve('src/lib/components/home/FirstWeekInsightBanner.svelte'),
  'utf8'
);

describe('/ home screen ownership contract', () => {
  it('keeps advanced insight journey UI off the daily touch point', () => {
    expect(source).not.toContain('InsightJourneyBanner');
    expect(source).not.toContain('InsightPhaseMilestoneCard');
    expect(source).not.toContain('shouldShowMaturityMilestone');
  });

  it('does not duplicate app navigation or session controls on Home', () => {
    expect(source).not.toContain('home-links');
    expect(source).not.toContain('home-logout');
    expect(source).not.toContain('handleLogout');
  });

  it('exposes weekly analysis bridge links from the daily brief', () => {
    expect(homeDailyBriefSource).toContain('href="/insights"');
    expect(homeDailyBriefSource).toContain('href="/trends"');
    expect(homeDailyBriefSource).toContain('data-testid="home-weekly-bridge"');
    expect(firstWeekBannerSource).not.toContain('href="/insights"');
  });

  it('uses the shared Button primitive for entry actions', () => {
    const todayContextSource = readFileSync(
      resolve('src/lib/components/home/HomeTodayContext.svelte'),
      'utf8'
    );
    expect(source).toContain('$lib/components/common/Button.svelte');
    expect(source).toContain('data-testid="home-cta"');
    expect(todayContextSource).toContain('data-testid="home-today-action"');
  });
});
