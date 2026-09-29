/**
 * Insights API client - M3 Sprint 6.
 *
 * Read-only surface for worker-generated analytics insights. The backend
 * storage/API names are intentionally kept stable; frontend copy remains
 * neutral and non-gamified.
 */

import { api } from './client';
import type { components } from '../../../../../packages/api-types/src/schema';

// Generated OpenAPI shapes (issue #778) — re-exported so the contract drift
// guard in ./contracts.generated.ts is part of the real import graph.
export type { ApiInsightResponse, ApiInsightListResponse } from './contracts.generated';

export type InsightType =
  | 'pointbiserial'
  | 'null_association'
  | 'spearman'
  | 'weekday_pattern'
  | 'work_context_pattern'
  | 'weekday_context_pattern'
  | (string & {});
export type InsightTier = 'none' | 'early' | 'preliminary' | 'developing' | 'robust';
export type InsightMaturityPhase = 'collecting' | 'early_patterns' | 'provisional' | 'robust';

/** Versioned API evidence union; incomplete historical rows may be null. */
export type InsightEvidence = NonNullable<components['schemas']['InsightResponse']['evidence']>;

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
  /** Versioned family evidence; null for incomplete historical payloads. */
  evidence?: InsightEvidence | null;
  generated_for_date: string;
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export interface InsightListResponse {
  insight_maturity: InsightMaturity;
  insights: InsightResponse[];
  /**
   * Timestamp of the latest completed generation attempt for this user.
   * This can be newer than every persisted row when a run correctly found no
   * candidates, so freshness must prefer it over `generated_at`.
   */
  last_successful_insight_run_at?: string | null;
  /** Latest finished USER_INSIGHTS attempt (Home compact worker status). */
  last_insight_run?: InsightWorkerRunSummary | null;
}

export interface InsightWorkerRunSummary {
  status: 'succeeded' | 'failed' | 'never_run';
  finished_at: string | null;
  started_at: string | null;
  insight_count: number | null;
  trigger_source: string | null;
  generated_for_date: string | null;
}

export interface InsightDigestItem {
  id: string;
  insight_type: InsightType;
  metric: string;
  effect_size: number | null;
  confidence: number | null;
  statement: string | null;
}

export interface InsightDigestResponse {
  week_start: string;
  week_end: string;
  insight_count: number;
  insights: InsightDigestItem[];
  push_title: string;
  push_body: string;
  // #739: set for a persisted weekly digest, null for the on-demand recompute
  // fallback. Only a stored digest (stable timestamp) drives the one-time modal.
  generated_at?: string | null;
}

export interface InsightListQuery {
  limit?: number;
}

/**
 * `/insights/latest` only. The chronological `/insights` endpoint declares no
 * family filter, so a shared query type would advertise — and silently drop —
 * an option that endpoint ignores.
 */
export interface LatestInsightListQuery extends InsightListQuery {
  /**
   * Restrict to these insight families *before* the row cap applies. A surface
   * that renders one or two families otherwise loses valid rows to unrelated
   * subjects occupying the first `limit` slots (#959).
   */
  insightTypes?: readonly string[];
}

  analysis_status?: CooccurrenceAnalysisStatus;
  analysis_limit?: CooccurrenceAnalysisLimit | null;
