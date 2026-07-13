import { describe, expect, it } from 'vitest';
import type { TagClustersResponse } from '$lib/api/insights';
import {
  getTagGroupsInsufficientKey,
  getTagGroupsInsufficientValues,
  getTagGroupsSubtitleKey,
  showTagClusterMaturityBadge,
} from './tagGroupsPresentation';

function makeClusters(overrides: Partial<TagClustersResponse> = {}): TagClustersResponse {
  return {
    status: 'ok',
    entry_count: 67,
    active_tag_count: 6,
    active_signal_count: 6,
    window_days: 67,
    k: 3,
    reason: null,
    cluster_kind: 'tags_only',
    cluster_maturity: 'provisional',
    cluster_mode: 'kmeans',
    entries_until_robust: 23,
    silhouette_score: 0.115,
    clusters: [],
    ...overrides,
  };
}

describe('tagGroupsPresentation', () => {
  it('shows maturity badge for provisional and early only', () => {
    expect(showTagClusterMaturityBadge(makeClusters({ cluster_maturity: 'provisional' }))).toBe(
      true
    );
    expect(showTagClusterMaturityBadge(makeClusters({ cluster_maturity: 'early' }))).toBe(true);
    expect(showTagClusterMaturityBadge(makeClusters({ cluster_maturity: 'robust' }))).toBe(false);
    expect(showTagClusterMaturityBadge(null)).toBe(false);
  });

  it('selects subtitle keys by cluster mode and maturity', () => {
    expect(getTagGroupsSubtitleKey(makeClusters())).toBe(
      'insights.tag_groups.subtitle_kmeans_provisional'
    );
    expect(
      getTagGroupsSubtitleKey(
        makeClusters({ cluster_mode: 'pair', cluster_maturity: 'early', k: null })
      )
    ).toBe('insights.tag_groups.subtitle_pair');
    expect(
      getTagGroupsSubtitleKey(
        makeClusters({ cluster_kind: 'mixed', cluster_maturity: 'robust', cluster_mode: 'kmeans' })
      )
    ).toBe('insights.tag_groups.subtitle_mixed');
  });

  it('uses pair threshold copy for 25-day insufficient state', () => {
    const data = makeClusters({
      status: 'insufficient_data',
      entry_count: 25,
      active_tag_count: 4,
      active_signal_count: 4,
      reason: 'entry_count_below_30',
      cluster_maturity: null,
      cluster_mode: null,
      entries_until_robust: 65,
    });

    expect(getTagGroupsInsufficientKey(data)).toBe('insights.tag_groups.insufficient_below_pair');
    expect(getTagGroupsInsufficientValues(data)).toEqual({
      entries: 25,
      remaining: 5,
      target: 30,
      tags: 4,
    });
  });

  it('uses tag threshold copy when entries are enough but signals are not', () => {
    const data = makeClusters({
      status: 'insufficient_data',
      entry_count: 40,
      active_tag_count: 3,
      active_signal_count: 3,
      reason: 'active_signal_count_below_5',
      cluster_maturity: null,
      cluster_mode: null,
    });

    expect(getTagGroupsInsufficientKey(data)).toBe('insights.tag_groups.insufficient_tags');
    expect(getTagGroupsInsufficientValues(data).target).toBe(5);
  });
});
