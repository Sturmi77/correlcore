import type {
  InsightMaturityPhase,
  InsightResponse,
  SymptomTagCooccurrenceResponse,
  TagCooccurrenceResponse,
} from '$lib/api/insights';
import { MATRIX_TAB_MIN_INSIGHTS, countMatrixInsights } from '$lib/utils/insightMatrixGate';

const EARLY_PHASES: InsightMaturityPhase[] = ['early_patterns', 'provisional', 'robust'];
const PROVISIONAL_PHASES: InsightMaturityPhase[] = ['provisional', 'robust'];

export function canShowAdvancedAnalytics(phase: InsightMaturityPhase | null): boolean {
  return phase !== null && phase !== 'collecting';
}

export function canShowMatrixTab(
  phase: InsightMaturityPhase | null,
  insights: readonly InsightResponse[]
): boolean {
  return (
    phase !== null &&
    EARLY_PHASES.includes(phase) &&
    countMatrixInsights(insights) >= MATRIX_TAB_MIN_INSIGHTS
  );
}

export function canShowTagCooccurrence(phase: InsightMaturityPhase | null): boolean {
  return phase !== null && EARLY_PHASES.includes(phase);
}

export function canShowSymptomCooccurrence(phase: InsightMaturityPhase | null): boolean {
  return phase !== null && PROVISIONAL_PHASES.includes(phase);
}

export function hasTagCooccurrenceData(
  data: TagCooccurrenceResponse | null,
  minPairs = 1
): boolean {
  return (data?.pairs.length ?? 0) >= minPairs;
}

export function hasSymptomCooccurrenceData(data: SymptomTagCooccurrenceResponse | null): boolean {
  return (data?.cells.length ?? 0) > 0;
}
