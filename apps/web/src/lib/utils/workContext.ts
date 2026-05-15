import type { WorkContext } from '$lib/api/entries';

/**
 * Default work context from calendar date (Issue #171).
 * Weekends → `weekend`; weekdays → `homeoffice` (overridable in the form).
 */
export function defaultWorkContextForDate(date: Date): WorkContext {
  const dow = date.getDay();
  if (dow === 0 || dow === 6) return 'weekend';
  return 'homeoffice';
}
