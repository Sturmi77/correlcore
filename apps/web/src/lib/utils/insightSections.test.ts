import { describe, expect, it } from 'vitest';
import {
  DEFAULT_INSIGHT_SECTIONS,
  isInsightSectionLocked,
  mergeInsightSections,
  normalizeInsightSectionsForSave,
  resolveEnabledInsightSections,
  type InsightSectionKey,
} from './insightSections';

describe('insightSections', () => {
  it('returns defaults when stored is null or empty', () => {
    expect(mergeInsightSections(null)).toEqual(DEFAULT_INSIGHT_SECTIONS);
    expect(mergeInsightSections([])).toEqual(DEFAULT_INSIGHT_SECTIONS);
  });

  it('preserves user order and merges missing keys', () => {
    const merged = mergeInsightSections([
      { key: 'tag_groups', enabled: true },
      { key: 'correlation_matrix', enabled: false },
    ]);

    expect(merged.slice(0, 2).map((section) => section.key)).toEqual([
      'tag_groups',
      'correlation_matrix',
    ]);
    expect(merged[1]?.enabled).toBe(false);
    // Missing keys are appended so the feed is never lost.
    expect(merged.some((section) => section.key === 'insight_feed')).toBe(true);
  });

  it('drops unknown keys', () => {
    const merged = mergeInsightSections([
      { key: 'lag_heatmap', enabled: true },
      { key: 'legacy_block' as unknown as InsightSectionKey, enabled: true },
    ]);

    expect(merged.some((section) => (section.key as string) === 'legacy_block')).toBe(false);
  });

  it('forces the locked feed to stay enabled on merge', () => {
    const merged = mergeInsightSections([{ key: 'insight_feed', enabled: false }]);
    const feed = merged.find((section) => section.key === 'insight_feed');
    expect(feed?.enabled).toBe(true);
    expect(isInsightSectionLocked('insight_feed')).toBe(true);
    expect(isInsightSectionLocked('lag_heatmap')).toBe(false);
  });

  it('resolves enabled sections only', () => {
    const enabled = resolveEnabledInsightSections([
      { key: 'insight_feed', enabled: true },
      { key: 'lag_heatmap', enabled: false },
    ]);

    expect(enabled).toEqual([{ key: 'insight_feed', enabled: true }]);
  });

  it('normalizes save payload, dedupes keys and keeps the feed enabled', () => {
    const normalized = normalizeInsightSectionsForSave([
      { key: 'lag_heatmap', enabled: true },
      { key: 'lag_heatmap', enabled: false },
      { key: 'not_real' as 'lag_heatmap', enabled: true },
      { key: 'insight_feed', enabled: false },
    ]);

    expect(normalized).toEqual([
      { key: 'lag_heatmap', enabled: true },
      { key: 'insight_feed', enabled: true },
    ]);
  });
});
