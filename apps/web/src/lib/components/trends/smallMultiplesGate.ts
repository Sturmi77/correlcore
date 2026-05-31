/**
 * smallMultiplesGate — M3.8 Sprint 3 (ADR-0035 §6 + ADR-0021).
 *
 * Single source of truth for the phase gate that protects the
 * Event-Aligned Small Multiples sheet. Both the sheet component and
 * any Insight card that offers the "Explore aligned events" affordance
 * import this helper so the gate semantics stay aligned across call
 * sites.
 */

import type { InsightMaturityPhase } from '$lib/api/insights';

/** Window radius around the onset, in days. */
export const SMALL_MULTIPLES_RADIUS = 7;

/**
 * Returns true when a phase-gated visualisation is allowed to render.
 * Sprint 3 / ADR-0021 + ADR-0035: small-multiples sheet is only safe
 * once we have at least provisional confidence (>=15 entries).
 */
export function isSmallMultiplesUnlocked(phase: InsightMaturityPhase | null | undefined): boolean {
  return phase === 'provisional' || phase === 'robust';
}
