/**
 * Strip pre-#632 per-statement safety tails from persisted insight copy.
 *
 * New generations no longer append these suffixes (see insight_engine.py).
 * Older encrypted rows / digest snapshots may still contain them; strip at
 * presentation time so the feed header is not duplicated by card text.
 */
const LEGACY_STATEMENT_TAILS: readonly string[] = [
  ' This is a data pattern, not a diagnosis.',
  ' Treat this as a pattern to reflect on, not a cause.',
  ' This is an early calendar pattern, not a diagnosis.',
  ' This is an early context pattern, not a diagnosis.',
  ' This is an early calendar/context pattern, not a diagnosis.',
  ' This is a multivariate pattern, not a cause.',
  ' Treat this as a time-shifted pattern, not a cause.',
  ' Treat this as an association, not a cause.',
  ' This is a co-occurrence pattern, not a cause.',
  ' This is a descriptive pattern, not a diagnosis.',
];

export function stripLegacyInsightStatementTails(statement: string | null | undefined): string {
  if (!statement) return '';
  let result = statement;
  let changed = true;
  while (changed) {
    changed = false;
    const trimmedEnd = result.trimEnd();
    for (const tail of LEGACY_STATEMENT_TAILS) {
      if (trimmedEnd.endsWith(tail)) {
        result = trimmedEnd.slice(0, -tail.length).trimEnd();
        changed = true;
        break;
      }
    }
  }
  return result;
}
