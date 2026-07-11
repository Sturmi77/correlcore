import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const trendsSource = readFileSync(resolve('src/routes/trends/+page.svelte'), 'utf8');
const trendsToolbarSource = readFileSync(
  resolve('src/lib/components/trends/TrendsAnalysisToolbar.svelte'),
  'utf8'
);
const insightsRouteSource = readFileSync(resolve('src/routes/insights/+page.svelte'), 'utf8');
const settingsSource = readFileSync(resolve('src/routes/settings/+page.svelte'), 'utf8');
const insightFeedSource = readFileSync(
  resolve('src/lib/components/insights/InsightFeed.svelte'),
  'utf8'
);

describe('control primitive contract', () => {
  it('uses a dedicated sticky toolbar for the global Trends range', () => {
    expect(trendsSource).toContain('TrendsAnalysisToolbar');
    expect(trendsToolbarSource).toContain('trends-toolbar');
    expect(trendsToolbarSource).toContain('data-testid="trends-sticky-toolbar"');
    expect(trendsSource).not.toContain('trends__controls');
  });

  it('uses TabBar for Trends and Insights tabs', () => {
    expect(trendsSource).toContain('TrendsAnalysisToolbar');
    expect(trendsToolbarSource).toContain('$lib/components/common/TabBar.svelte');
    expect(trendsToolbarSource).toContain('<TabBar');
    expect(trendsSource).not.toContain('trends__tabs');

    expect(insightFeedSource).toContain('$lib/components/common/TabBar.svelte');
    expect(insightFeedSource).toContain('<TabBar');
    expect(insightFeedSource).not.toContain('if-tabs');
    expect(insightFeedSource).not.toContain('if-tab');

    expect(insightsRouteSource).toContain(
      '$lib/components/insights/InsightsAnalysisToolbar.svelte'
    );
    expect(insightsRouteSource).toContain('<InsightsAnalysisToolbar');
    expect(insightsRouteSource).not.toContain('insights-page__view-toggle');
  });

  it('uses shared controls for settings selections and actions', () => {
    expect(settingsSource).toContain('$lib/components/common/SegmentedControl.svelte');
    expect(settingsSource).toContain('<SegmentedControl');
    expect(settingsSource).not.toContain('settings__language button');
    expect(settingsSource).not.toContain('class="btn');
  });
});
