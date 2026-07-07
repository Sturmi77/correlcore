import type { WorkContext } from '$lib/api/entries';
import type { WorkContextTypical } from '$lib/api/profile';

/**
 * Default work context from calendar date (Issue #171).
 * Weekends -> `weekend`; weekdays use the optional onboarding profile
 * where it maps cleanly to the entry enum (overridable in the form).
 */
export function defaultWorkContextForDate(
  date: Date,
  typical: WorkContextTypical | null = null
): WorkContext {
  const dow = date.getDay();
  if (dow === 0 || dow === 6) return 'weekend';
  if (typical === 'office') return 'office';
  if (typical === 'remote') return 'homeoffice';
  return 'homeoffice';
}
