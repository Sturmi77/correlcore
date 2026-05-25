import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const trendsSource = readFileSync(resolve('src/routes/trends/+page.svelte'), 'utf8');
const insightFeedSource = readFileSync(
  resolve('src/lib/components/insights/InsightFeed.svelte'),
  'utf8'
);

describe('control primitive contract', () => {
  it('uses SegmentedControl for trend range filters', () => {
    expect(trendsSource).toContain('$lib/components/common/SegmentedControl.svelte');
    expect(trendsSource).toContain('<SegmentedControl');
    expect(trendsSource).not.toContain('trends__segments');
  });

  it('uses TabBar for Trends and Insights tabs', () => {
    expect(trendsSource).toContain('$lib/components/common/TabBar.svelte');
    expect(trendsSource).toContain('<TabBar');
    expect(trendsSource).not.toContain('trends__tabs');

    expect(insightFeedSource).toContain('$lib/components/common/TabBar.svelte');
    expect(insightFeedSource).toContain('<TabBar');
    expect(insightFeedSource).not.toContain('if-tabs');
    expect(insightFeedSource).not.toContain('if-tab');
  });
});
