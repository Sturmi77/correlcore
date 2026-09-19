/**
 * Shared confidence → semantic label mapping used by InsightEvidence and
 * surfaces that must speak the same vocabulary (matrix, habits).
 *
 * Boundaries: [0,0.2) early | [0.2,0.4) emerging | [0.4,0.6) moderate
 *             [0.6,0.8) strong | [0.8,1] very_strong
 */
export type ConfidenceLabelKey =
  | 'early_signal'
  | 'emerging_pattern'
  | 'moderate_finding'
  | 'strong_finding'
  | 'very_strong_finding';

export function confidenceLabelKey(score: number): ConfidenceLabelKey {
  const clamped = Math.min(1, Math.max(0, score));
  if (clamped < 0.2) return 'early_signal';
  if (clamped < 0.4) return 'emerging_pattern';
  if (clamped < 0.6) return 'moderate_finding';
  if (clamped < 0.8) return 'strong_finding';
  return 'very_strong_finding';
}
