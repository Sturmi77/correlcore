import { describe, expect, it } from 'vitest';
import migrationCases from '../../../../../tests/fixtures/insight_sections_migration.json';
import {
  CURRENT_INSIGHT_SECTIONS_VERSION,
  DEFAULT_INSIGHT_SECTIONS,
  isInsightSectionLocked,
  LEGACY_DEFAULT_INSIGHT_SECTIONS,
  mergeInsightSections,
  migrateInsightSectionsToCurrent,
  normalizeInsightSectionsForSave,
  resolveEnabledInsightSections,
  type InsightSectionKey,
} from './insightSections';

describe('insightSections', () => {
  it('returns slim defaults when stored is null or empty', () => {
    expect(mergeInsightSections(null)).toEqual(DEFAULT_INSIGHT_SECTIONS);
    expect(mergeInsightSections([])).toEqual(DEFAULT_INSIGHT_SECTIONS);
    expect(DEFAULT_INSIGHT_SECTIONS.find((s) => s.key === 'correlation_matrix')?.enabled).toBe(
      false
    );
    expect(DEFAULT_INSIGHT_SECTIONS.find((s) => s.key === 'insight_feed')?.enabled).toBe(true);
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

  it('has stage_header as a default, non-locked section (#823)', () => {
    expect(DEFAULT_INSIGHT_SECTIONS[0]?.key).toBe('stage_header');
    expect(isInsightSectionLocked('stage_header')).toBe(false);
    const normalized = normalizeInsightSectionsForSave([{ key: 'stage_header', enabled: false }]);
    expect(normalized).toEqual([{ key: 'stage_header', enabled: false }]);
    const merged = mergeInsightSections([{ key: 'stage_header', enabled: false }]);
    expect(merged.find((section) => section.key === 'stage_header')?.enabled).toBe(false);
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

describe('migrateInsightSectionsToCurrent (Phase 6)', () => {
  it('is a no-op when already on the current version', () => {
    const result = migrateInsightSectionsToCurrent(LEGACY_DEFAULT_INSIGHT_SECTIONS, 2);
    expect(result.dirty).toBe(false);
    expect(result.version).toBe(2);
  });

  it('replaces exact legacy defaults with the slim layout', () => {
    const result = migrateInsightSectionsToCurrent(LEGACY_DEFAULT_INSIGHT_SECTIONS, 1);
    expect(result.dirty).toBe(true);
    expect(result.version).toBe(CURRENT_INSIGHT_SECTIONS_VERSION);
    expect(result.sections).toEqual(DEFAULT_INSIGHT_SECTIONS);
  });

  it('keeps all enabled flags on a customized layout', () => {
    const result = migrateInsightSectionsToCurrent(
      [
        { key: 'stage_header', enabled: true },
        { key: 'correlation_matrix', enabled: true },
        { key: 'insight_feed', enabled: true },
        { key: 'lag_heatmap', enabled: false },
        { key: 'dismissed', enabled: true },
        { key: 'symptom_analytics', enabled: true },
        { key: 'tag_groups', enabled: true },
        { key: 'tag_cooccurrence', enabled: true },
      ],
      1
    );
    expect(result.dirty).toBe(true);
    const byKey = new Map(result.sections?.map((section) => [section.key, section.enabled]));
    expect(byKey.get('lag_heatmap')).toBe(false);
    expect(byKey.get('correlation_matrix')).toBe(true);
    expect(byKey.get('insight_feed')).toBe(true);
  });

  it('only bumps version when stored is empty', () => {
    const result = migrateInsightSectionsToCurrent(null, 1);
    expect(result).toEqual({
      sections: null,
      version: CURRENT_INSIGHT_SECTIONS_VERSION,
      dirty: true,
    });
  });

  it.each(migrationCases)('matches shared fixture $name', ({ stored, expected }) => {
    const asSections = (pairs: (string | boolean)[][]) =>
      pairs.map(([key, enabled]) => ({
        key: key as InsightSectionKey,
        enabled: enabled as boolean,
      }));
    const result = migrateInsightSectionsToCurrent(asSections(stored), 1);
    expect(result).toEqual({ sections: asSections(expected), version: 2, dirty: true });
    expect(migrateInsightSectionsToCurrent(result.sections, result.version)).toEqual({
      sections: asSections(expected),
      version: 2,
      dirty: false,
    });
  });
});
