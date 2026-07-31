import type { HomeSectionKey, HomeSectionPreference } from '$lib/api/preferences';

export type { HomeSectionKey, HomeSectionPreference };

export const DEFAULT_HOME_SECTIONS: HomeSectionPreference[] = [
  { key: 'first_week_banner', enabled: true },
  { key: 'daily_brief', enabled: true },
  { key: 'work_context', enabled: true },
  { key: 'weekday_overview', enabled: true },
];

const VALID_HOME_SECTION_KEYS = new Set<HomeSectionKey>([
  'first_week_banner',
  'daily_brief',
  'work_context',
  'weekday_overview',
]);

function isHomeSectionKey(value: string): value is HomeSectionKey {
  return VALID_HOME_SECTION_KEYS.has(value as HomeSectionKey);
}

function coerceSection(raw: unknown): HomeSectionPreference | null {
  if (!raw || typeof raw !== 'object') return null;
  const record = raw as Record<string, unknown>;
  const key = record.key;
  const enabled = record.enabled;
  if (typeof key !== 'string' || !isHomeSectionKey(key.trim())) return null;
  if (typeof enabled !== 'boolean') return null;
  return { key: key.trim() as HomeSectionKey, enabled };
}

export function mergeHomeSections(
  stored: HomeSectionPreference[] | null | undefined
): HomeSectionPreference[] {
  if (!stored?.length) {
    return DEFAULT_HOME_SECTIONS.map((section) => ({ ...section }));
  }

  const merged: HomeSectionPreference[] = [];
  const seen = new Set<HomeSectionKey>();

  for (const raw of stored) {
    const section = coerceSection(raw);
    if (!section || seen.has(section.key)) continue;
    merged.push(section);
    seen.add(section.key);
  }

  for (const section of DEFAULT_HOME_SECTIONS) {
    if (!seen.has(section.key)) {
      merged.push({ ...section });
      seen.add(section.key);
    }
  }

  return merged;
}

export function resolveEnabledSections(
  sections: HomeSectionPreference[]
): HomeSectionPreference[] {
  return sections.filter((section) => section.enabled);
}

export function normalizeHomeSectionsForSave(
  sections: HomeSectionPreference[]
): HomeSectionPreference[] {
  const normalized: HomeSectionPreference[] = [];
  const seen = new Set<HomeSectionKey>();

  for (const raw of sections) {
    const section = coerceSection(raw);
    if (!section || seen.has(section.key)) continue;
    normalized.push(section);
    seen.add(section.key);
  }

  return normalized;
}
