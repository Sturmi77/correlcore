import type { InsightSectionKey, InsightSectionPreference } from '$lib/api/preferences';
import { createSectionUtils } from '$lib/utils/sectionPreferences';

export type { InsightSectionKey, InsightSectionPreference };

/** The main feed can never be hidden — only reordered. */
export const LOCKED_INSIGHT_SECTION_KEYS: InsightSectionKey[] = ['insight_feed'];

/** Pre-Phase-6 all-on layout — used only to detect "saved defaults". */
export const LEGACY_DEFAULT_INSIGHT_SECTIONS: InsightSectionPreference[] = [
  { key: 'stage_header', enabled: true },
  { key: 'correlation_matrix', enabled: true },
  { key: 'insight_feed', enabled: true },
  { key: 'lag_heatmap', enabled: true },
  { key: 'dismissed', enabled: true },
  { key: 'symptom_analytics', enabled: true },
  { key: 'tag_groups', enabled: true },
  { key: 'tag_cooccurrence', enabled: true },
];

/**
 * Phase 6 / D5 slim Layer-1 default. Optional blocks stay in validKeys so
 * Settings can re-enable them; they are no longer in the entry viewport.
 */
export const DEFAULT_INSIGHT_SECTIONS: InsightSectionPreference[] = [
  { key: 'stage_header', enabled: true },
  { key: 'insight_feed', enabled: true },
  { key: 'correlation_matrix', enabled: false },
  { key: 'lag_heatmap', enabled: false },
  { key: 'dismissed', enabled: false },
  { key: 'symptom_analytics', enabled: false },
  { key: 'tag_groups', enabled: false },
  { key: 'tag_cooccurrence', enabled: false },
];

export const SHRINK_INSIGHT_SECTION_KEYS: InsightSectionKey[] = [
  'correlation_matrix',
  'lag_heatmap',
  'dismissed',
  'symptom_analytics',
  'tag_groups',
  'tag_cooccurrence',
];

export const CURRENT_INSIGHT_SECTIONS_VERSION = 2;
export const LEGACY_INSIGHT_SECTIONS_VERSION = 1;

const VALID_INSIGHT_SECTION_KEYS: InsightSectionKey[] = [
  'stage_header',
  'correlation_matrix',
  'insight_feed',
  'lag_heatmap',
  'dismissed',
  'symptom_analytics',
  'tag_groups',
  'tag_cooccurrence',
];

const insightSectionUtils = createSectionUtils<InsightSectionKey>({
  validKeys: VALID_INSIGHT_SECTION_KEYS,
  defaults: DEFAULT_INSIGHT_SECTIONS,
  lockedKeys: LOCKED_INSIGHT_SECTION_KEYS,
});

export function mergeInsightSections(
  stored: InsightSectionPreference[] | null | undefined
): InsightSectionPreference[] {
  return insightSectionUtils.merge(stored);
}

export function resolveEnabledInsightSections(
  sections: InsightSectionPreference[]
): InsightSectionPreference[] {
  return insightSectionUtils.resolveEnabled(sections);
}

export function normalizeInsightSectionsForSave(
  sections: InsightSectionPreference[]
): InsightSectionPreference[] {
  return insightSectionUtils.normalizeForSave(sections);
}

export function isInsightSectionLocked(key: InsightSectionKey): boolean {
  return insightSectionUtils.isLocked(key);
}

function sameLayout(
  left: readonly InsightSectionPreference[],
  right: readonly InsightSectionPreference[]
): boolean {
  if (left.length !== right.length) return false;
  return left.every(
    (section, index) =>
      section.key === right[index]?.key && section.enabled === right[index]?.enabled
  );
}

/**
 * Client-side mirror of the backend v1→v2 migrate (offline / tests).
 * Prefer trusting GET /user/preferences after the server has persisted.
 */
export function migrateInsightSectionsToCurrent(
  stored: InsightSectionPreference[] | null | undefined,
  version: number | null | undefined
): { sections: InsightSectionPreference[] | null; version: number; dirty: boolean } {
  const currentVersion = version ?? LEGACY_INSIGHT_SECTIONS_VERSION;
  if (currentVersion >= CURRENT_INSIGHT_SECTIONS_VERSION) {
    return {
      sections: stored?.length ? normalizeInsightSectionsForSave(stored) : null,
      version: currentVersion,
      dirty: false,
    };
  }

  if (!stored?.length) {
    return { sections: null, version: CURRENT_INSIGHT_SECTIONS_VERSION, dirty: true };
  }

  const normalized = normalizeInsightSectionsForSave(stored);
  if (sameLayout(stored, LEGACY_DEFAULT_INSIGHT_SECTIONS)) {
    return {
      sections: DEFAULT_INSIGHT_SECTIONS.map((section) => ({ ...section })),
      version: CURRENT_INSIGHT_SECTIONS_VERSION,
      dirty: true,
    };
  }

  return {
    // Preserve explicit order and flags. Missing known keys get current defaults.
    sections: insightSectionUtils.merge(normalized),
    version: CURRENT_INSIGHT_SECTIONS_VERSION,
    dirty: true,
  };
}

/** Optional hub tools that live behind Settings when off by default. */
export const INSIGHT_TOOL_SECTION_KEYS: InsightSectionKey[] = [
  'symptom_analytics',
  'tag_groups',
  'tag_cooccurrence',
  'lag_heatmap',
  'correlation_matrix',
];
