import type { TagSuggestion } from '$lib/api/onboarding';

/**
 * Session-scoped stash for EntryForm onboarding suggestion picks.
 *
 * Picks live in an in-memory Map that is destroyed when BottomSheet closes
 * ({#if open} tears down EntryForm). After an offline-deferred first save,
 * entry_count becomes > 0 and shouldShowOnboardingTags would hide chips
 * forever while onboarding_retro_completed stays false. Persist picks here
 * so a remount can restore them and retry completeOnboarding.
 *
 * Scoped by user id to avoid cross-account leakage in the same tab.
 */
const STORAGE_KEY_PREFIX = 'cc_onboarding_suggestion_stash:';

export interface OnboardingSuggestionStash {
  userId: string;
  suggestions: TagSuggestion[];
  finalizeDeferred: boolean;
}

function storageKey(userId: string): string {
  return `${STORAGE_KEY_PREFIX}${userId}`;
}

function canUseSessionStorage(): boolean {
  return typeof sessionStorage !== 'undefined';
}

/**
 * True when a deferred finalize stash exists (offline/failed completeOnboarding
 * awaiting retry). Toggle-only stashes (`finalizeDeferred: false`) do not count —
 * those must not re-open the onboarding chip gate after entry_count > 0.
 */
export function hasOnboardingSuggestionStash(userId: string): boolean {
  const stash = readOnboardingSuggestionStash(userId);
  return stash?.finalizeDeferred === true;
}

export function readOnboardingSuggestionStash(userId: string): OnboardingSuggestionStash | null {
  if (!userId || !canUseSessionStorage()) return null;
  try {
    const raw = sessionStorage.getItem(storageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<OnboardingSuggestionStash>;
    if (parsed.userId !== userId || !Array.isArray(parsed.suggestions)) return null;
    return {
      userId,
      suggestions: parsed.suggestions.filter(isTagSuggestion),
      finalizeDeferred: Boolean(parsed.finalizeDeferred),
    };
  } catch {
    return null;
  }
}

export function writeOnboardingSuggestionStash(stash: OnboardingSuggestionStash): void {
  if (!stash.userId || !canUseSessionStorage()) return;
  try {
    // storage-exempt: per-user key is STORAGE_KEY_PREFIX + userId; holds only
    // onboarding tag-suggestion picks (no auth material), scoped per account.
    sessionStorage.setItem(storageKey(stash.userId), JSON.stringify(stash));
  } catch {
    /* quota / private mode — best-effort */
  }
}

export function clearOnboardingSuggestionStash(userId: string): void {
  if (!userId || !canUseSessionStorage()) return;
  try {
    sessionStorage.removeItem(storageKey(userId));
  } catch {
    /* ignore */
  }
}

/** Drop every onboarding stash in this tab (logout / account switch). */
export function clearAllOnboardingSuggestionStashes(): void {
  if (!canUseSessionStorage()) return;
  try {
    const keys: string[] = [];
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const key = sessionStorage.key(i);
      if (key?.startsWith(STORAGE_KEY_PREFIX)) keys.push(key);
    }
    for (const key of keys) sessionStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

function isTagSuggestion(value: unknown): value is TagSuggestion {
  if (!value || typeof value !== 'object') return false;
  const row = value as Partial<TagSuggestion>;
  return (
    typeof row.slug === 'string' && typeof row.name === 'string' && typeof row.category === 'string'
  );
}
