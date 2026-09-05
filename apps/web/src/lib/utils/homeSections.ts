import type { HomeSectionKey, HomeSectionPreference } from '$lib/api/preferences';
import { createSectionUtils } from '$lib/utils/sectionPreferences';

export type { HomeSectionKey, HomeSectionPreference };

export const DEFAULT_HOME_SECTIONS: HomeSectionPreference[] = [
  { key: 'first_week_banner', enabled: true },
  { key: 'daily_brief', enabled: true },
  { key: 'work_context', enabled: true },
  { key: 'weekday_overview', enabled: true },
];

const homeSectionUtils = createSectionUtils<HomeSectionKey>({
  validKeys: ['first_week_banner', 'daily_brief', 'work_context', 'weekday_overview'],
  defaults: DEFAULT_HOME_SECTIONS,
});

export function mergeHomeSections(
  stored: HomeSectionPreference[] | null | undefined
): HomeSectionPreference[] {
  return homeSectionUtils.merge(stored);
}

export function resolveEnabledSections(sections: HomeSectionPreference[]): HomeSectionPreference[] {
  return homeSectionUtils.resolveEnabled(sections);
}

export function normalizeHomeSectionsForSave(
  sections: HomeSectionPreference[]
): HomeSectionPreference[] {
  return homeSectionUtils.normalizeForSave(sections);
}
