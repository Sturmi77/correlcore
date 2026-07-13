/**
 * Insight quality helpers — distinct day-entry dates for maturity/readiness UI.
 */

/** Collect distinct `slot=day` dates from API entries. */
export function dayEntryDatesFromIsoEntries(
  entries: readonly { entry_date: string; slot: string }[]
): string[] {
  const dates = new Set<string>();
  for (const e of entries) {
    if (e.slot === 'day') dates.add(e.entry_date);
  }
  return [...dates].sort();
}
