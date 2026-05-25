import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(resolve('src/routes/+page.svelte'), 'utf8');

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

  it('uses the shared Button primitive for the primary CTA', () => {
    expect(source).toContain('$lib/components/common/Button.svelte');
    expect(source).toContain('data-testid="home-cta"');
  });
});
