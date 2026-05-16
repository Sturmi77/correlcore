import type { InsightResponse } from '$lib/api/insights';
import { localIsoDate } from '$lib/utils/streak';

const today = localIsoDate(new Date());

export const mockInsights: InsightResponse[] = [
  {
    id: 'mock-insight-energy-mood',
    user_id: 'mock-user',
    insight_type: 'spearman',
    tier: 'developing',
    metric: 'mood',
    subject_type: 'metric',
    subject_id: 'energy',
    subject_label: 'Energy',
    effect_size: 0.58,
    confidence: 0.72,
    sample_n: 42,
    statement:
      'Mock data shows mood and energy moving together across recent entries. This is sample data for visual review.',
    flags: { causal_claim: false, mock: true },
    payload: {},
    generated_for_date: today,
    generated_at: `${today}T09:00:00Z`,
    created_at: `${today}T09:00:00Z`,
    updated_at: `${today}T09:00:00Z`,
  },
  {
    id: 'mock-insight-tag-focus',
    user_id: 'mock-user',
    insight_type: 'pointbiserial',
    tier: 'preliminary',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: 'focus',
    subject_label: 'Focus work',
    effect_size: 0.36,
    confidence: 0.54,
    sample_n: 28,
    statement:
      'Mock data shows a descriptive association between focus-work tags and mood scores.',
    flags: { causal_claim: false, mock: true },
    payload: {},
    generated_for_date: today,
    generated_at: `${today}T09:00:00Z`,
    created_at: `${today}T09:00:00Z`,
    updated_at: `${today}T09:00:00Z`,
  },
];
