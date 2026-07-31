import { describe, expect, it } from 'vitest';
import {
  DEFAULT_HOME_SECTIONS,
  mergeHomeSections,
  normalizeHomeSectionsForSave,
  resolveEnabledSections,
  type HomeSectionKey,
} from './homeSections';

describe('homeSections', () => {
  it('returns defaults when stored is null or empty', () => {
    expect(mergeHomeSections(null)).toEqual(DEFAULT_HOME_SECTIONS);
    expect(mergeHomeSections([])).toEqual(DEFAULT_HOME_SECTIONS);
  });

  it('preserves user order and merges missing keys', () => {
    const merged = mergeHomeSections([
      { key: 'weekday_overview', enabled: true },
      { key: 'daily_brief', enabled: false },
    ]);

    expect(merged.map((section) => section.key)).toEqual([
      'weekday_overview',
      'daily_brief',
      'first_week_banner',
      'work_context',
    ]);
    expect(merged[1]?.enabled).toBe(false);
  });

  it('drops unknown keys', () => {
    const merged = mergeHomeSections([
      { key: 'daily_brief', enabled: true },
      { key: 'legacy_block' as unknown as HomeSectionKey, enabled: true },
    ]);

    expect(merged.some((section) => (section.key as string) === 'legacy_block')).toBe(false);
  });

  it('resolves enabled sections only', () => {
    const enabled = resolveEnabledSections([
      { key: 'daily_brief', enabled: true },
      { key: 'work_context', enabled: false },
    ]);

    expect(enabled).toEqual([{ key: 'daily_brief', enabled: true }]);
  });

  it('normalizes save payload and dedupes keys', () => {
    const normalized = normalizeHomeSectionsForSave([
      { key: 'daily_brief', enabled: true },
      { key: 'daily_brief', enabled: false },
      { key: 'not_real' as 'daily_brief', enabled: true },
    ]);

    expect(normalized).toEqual([{ key: 'daily_brief', enabled: true }]);
  });
});
