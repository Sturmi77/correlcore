/**
 * Generic configurable-section utilities (#821).
 *
 * Shared merge/normalize/coerce logic behind the Home screen sections (#584)
 * and the Insights page sections (#821). Each caller builds its own set of
 * helpers via {@link createSectionUtils} with its valid keys, default order,
 * and optional locked keys (sections that must always stay enabled).
 */

export interface SectionPreference<K extends string = string> {
  key: K;
  enabled: boolean;
}

export interface SectionUtils<K extends string> {
  DEFAULTS: SectionPreference<K>[];
  merge(stored: SectionPreference<K>[] | null | undefined): SectionPreference<K>[];
  resolveEnabled(sections: SectionPreference<K>[]): SectionPreference<K>[];
  normalizeForSave(sections: SectionPreference<K>[]): SectionPreference<K>[];
  isLocked(key: K): boolean;
}

export function createSectionUtils<K extends string>(config: {
  validKeys: readonly K[];
  defaults: readonly SectionPreference<K>[];
  lockedKeys?: readonly K[];
}): SectionUtils<K> {
  const valid = new Set<string>(config.validKeys);
  const locked = new Set<string>(config.lockedKeys ?? []);
  const defaults = config.defaults;

  function isKey(value: string): value is K {
    return valid.has(value);
  }

  function coerce(raw: unknown): SectionPreference<K> | null {
    if (!raw || typeof raw !== 'object') return null;
    const record = raw as Record<string, unknown>;
    const key = record.key;
    const enabled = record.enabled;
    if (typeof key !== 'string' || !isKey(key.trim())) return null;
    if (typeof enabled !== 'boolean') return null;
    const trimmed = key.trim() as K;
    return { key: trimmed, enabled: locked.has(trimmed) ? true : enabled };
  }

  function merge(stored: SectionPreference<K>[] | null | undefined): SectionPreference<K>[] {
    if (!stored?.length) {
      return defaults.map((section) => ({ ...section }));
    }

    const merged: SectionPreference<K>[] = [];
    const seen = new Set<K>();

    for (const raw of stored) {
      const section = coerce(raw);
      if (!section || seen.has(section.key)) continue;
      merged.push(section);
      seen.add(section.key);
    }

    for (const section of defaults) {
      if (!seen.has(section.key)) {
        merged.push({ ...section });
        seen.add(section.key);
      }
    }

    return merged;
  }

  function resolveEnabled(sections: SectionPreference<K>[]): SectionPreference<K>[] {
    return sections.filter((section) => section.enabled);
  }

  function normalizeForSave(sections: SectionPreference<K>[]): SectionPreference<K>[] {
    const normalized: SectionPreference<K>[] = [];
    const seen = new Set<K>();

    for (const raw of sections) {
      const section = coerce(raw);
      if (!section || seen.has(section.key)) continue;
      normalized.push(section);
      seen.add(section.key);
    }

    return normalized;
  }

  return {
    DEFAULTS: defaults.map((section) => ({ ...section })),
    merge,
    resolveEnabled,
    normalizeForSave,
    isLocked: (key: K) => locked.has(key),
  };
}
