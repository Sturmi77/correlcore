import type { InsightResponse, InsightVerificationResponse } from '$lib/api/insights';

const SUPPORTED_METRICS = new Set(['mood_score', 'energy', 'stress', 'sleep_quality']);

/** Mirror the API's subject and metric limits before offering a scatter control. */
export function supportsInsightVerification(insight: InsightResponse): boolean {
  return (
    (insight.subject_type === 'tag' || insight.subject_type === 'symptom') &&
    SUPPORTED_METRICS.has(insight.metric) &&
    insight.payload?.method !== 'lag'
  );
}

export function hasUsableVerification(data: InsightVerificationResponse | null): boolean {
  return Boolean(
    data &&
    data.points.length > 0 &&
    data.with_n > 0 &&
    data.without_n > 0 &&
    data.with_mean !== null &&
    data.without_mean !== null
  );
}
