import type { InsightSectionKey, InsightSectionPreference } from '$lib/api/preferences';
import { createSectionUtils } from '$lib/utils/sectionPreferences';

export type { InsightSectionKey, InsightSectionPreference };

/** The main feed can never be hidden — only reordered. */
export const LOCKED_INSIGHT_SECTION_KEYS: InsightSectionKey[] = ['insight_feed'];

export const DEFAULT_INSIGHT_SECTIONS: InsightSectionPreference[] = [
  { key: 'correlation_matrix', enabled: true },
  { key: 'insight_feed', enabled: true },
  { key: 'lag_heatmap', enabled: true },
  { key: 'dismissed', enabled: true },
  { key: 'symptom_analytics', enabled: true },
  { key: 'tag_groups', enabled: true },
  { key: 'tag_cooccurrence', enabled: true },
];

const insightSectionUtils = createSectionUtils<InsightSectionKey>({
  validKeys: [
    'correlation_matrix',
    'insight_feed',
    'lag_heatmap',
    'dismissed',
    'symptom_analytics',
    'tag_groups',
    'tag_cooccurrence',
  ],
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
