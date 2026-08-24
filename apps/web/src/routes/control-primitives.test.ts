import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const trendsSource = readFileSync(resolve('src/routes/trends/+page.svelte'), 'utf8');
const trendsToolbarSource = readFileSync(
  resolve('src/lib/components/trends/TrendsAnalysisToolbar.svelte'),
  'utf8'
);
const insightsRouteSource = readFileSync(resolve('src/routes/insights/+page.svelte'), 'utf8');
const insightsToolbarSource = readFileSync(
  resolve('src/lib/components/insights/InsightsAnalysisToolbar.svelte'),
  'utf8'
);
const settingsSource = readFileSync(resolve('src/routes/settings/+page.svelte'), 'utf8');
const appearanceSettingsSource = readFileSync(
  resolve('src/routes/settings/appearance/+page.svelte'),
  'utf8'
);
const insightFeedSource = readFileSync(
  resolve('src/lib/components/insights/InsightFeed.svelte'),
  'utf8'
);

describe('control primitive contract', () => {
  it('melts the analysis toolbars into the sticky ScreenHeader controls slot (#703 Stage 2)', () => {
    expect(trendsSource).toContain('TrendsAnalysisToolbar');
    expect(trendsToolbarSource).toContain('trends-toolbar');
    expect(trendsToolbarSource).toContain('data-testid="trends-sticky-toolbar"');
    expect(trendsSource).not.toContain('trends__controls');

    // The header owns the sticky chrome now; both toolbars render inside its
    // `controls` slot and no longer position themselves sticky.
    expect(trendsSource).toContain('sticky');
    expect(trendsSource).toContain('slot="controls"');
    expect(insightsRouteSource).toContain('sticky');
    expect(insightsRouteSource).toContain('slot="controls"');
    expect(trendsToolbarSource).not.toContain('position: sticky');
    expect(insightsToolbarSource).not.toContain('position: sticky');
  });

  it('uses TabBar for Trends and Insights tabs', () => {
    expect(trendsSource).toContain('TrendsAnalysisToolbar');
    expect(trendsToolbarSource).toContain('$lib/components/common/TabBar.svelte');
    expect(trendsToolbarSource).toContain('<TabBar');
    expect(trendsSource).not.toContain('trends__tabs');

    // #685: the in-feed symptom/mood filter TabBar was removed — the feed no
    // longer renders any filter tabs.
    expect(insightFeedSource).not.toContain('<TabBar');
    expect(insightFeedSource).not.toContain('insight-feed-tabs');

    expect(insightsRouteSource).toContain(
      '$lib/components/insights/InsightsAnalysisToolbar.svelte'
    );
    expect(insightsRouteSource).toContain('<InsightsAnalysisToolbar');
    expect(insightsRouteSource).not.toContain('insights-page__view-toggle');
  });

  it('uses shared controls for settings selections and actions', () => {
    // #694: the language SegmentedControl now lives on the Appearance sub-page.
    expect(appearanceSettingsSource).toContain('$lib/components/common/SegmentedControl.svelte');
    expect(appearanceSettingsSource).toContain('<SegmentedControl');
    expect(appearanceSettingsSource).not.toContain('settings__language button');
    // The settings hub is a lean index — no raw button classes anywhere.
    expect(settingsSource).not.toContain('class="btn');
    expect(appearanceSettingsSource).not.toContain('class="btn');
  });
});
