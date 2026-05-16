import type { InsightMaturity, InsightMaturityPhase } from '$lib/api/insights';

export type MaturityMilestonePhase = Exclude<InsightMaturityPhase, 'collecting'>;

const milestonePhases: readonly MaturityMilestonePhase[] = [
  'early_patterns',
  'provisional',
  'robust',
];

export function maturityMilestoneKey(phase: InsightMaturityPhase): string | null {
  if (!milestonePhases.includes(phase as MaturityMilestonePhase)) return null;
  return `maturity_phase_${phase}`;
}

export function shouldShowMaturityMilestone(
  maturity: InsightMaturity | null,
  seenKeys: readonly string[] | undefined
): boolean {
  if (!maturity) return false;
  const key = maturityMilestoneKey(maturity.phase);
  if (!key) return false;
  return !(seenKeys ?? []).includes(key);
}
