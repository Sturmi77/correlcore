/**
 * Insights API client - M3 Sprint 6.
 *
 * Read-only surface for worker-generated analytics insights. The backend
 * storage/API names are intentionally kept stable; frontend copy remains
 * neutral and non-gamified.
 */

import { api } from './client';

export type InsightType = 'pointbiserial' | 'spearman' | 'weekday_pattern';
export type InsightTier = 'none' | 'early' | 'preliminary' | 'developing' | 'robust';
export type InsightMaturityPhase = 'collecting' | 'early_patterns' | 'provisional' | 'robust';

export interface InsightMaturity {
  phase: InsightMaturityPhase;
  phase_index: 1 | 2 | 3 | 4;
  current_entries: number;
  next_phase_at: number | null;
  next_phase_label: string | null;
  entries_until_next: number | null;
  user_message_key: string;
}

export interface InsightResponse {
  id: string;
  user_id: string;
  insight_type: InsightType;
  tier: InsightTier;
  metric: string;
  subject_type: string | null;
  subject_id: string | null;
  subject_label: string | null;
  effect_size: number | null;
  confidence: number | null;
  sample_n: number;
  statement: string | null;
  flags: Record<string, unknown>;
  payload: Record<string, unknown>;
  generated_for_date: string;
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export interface InsightListResponse {
  insight_maturity: InsightMaturity;
  insights: InsightResponse[];
}

export interface InsightListQuery {
  limit?: number;
}

function buildQuery(query: InsightListQuery): string {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

/** GET /insights - list generated insights newest-first. */
export async function listInsights(query: InsightListQuery = {}): Promise<InsightListResponse> {
  return api.get<InsightListResponse>(`/insights${buildQuery(query)}`);
}

/** GET /insights/latest - list latest generated insights by analytical subject. */
export async function listLatestInsights(
  query: InsightListQuery = {}
): Promise<InsightListResponse> {
  return api.get<InsightListResponse>(`/insights/latest${buildQuery(query)}`);
}

/** Convenience helper for the Home preview card. */
export async function fetchLatestInsight(): Promise<InsightResponse | null> {
  const response = await listLatestInsights({ limit: 1 });
  return response.insights[0] ?? null;
}
