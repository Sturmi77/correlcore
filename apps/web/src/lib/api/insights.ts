/**
 * Insights API client - M3 Sprint 6.
 *
 * Read-only surface for worker-generated analytics insights. The backend
 * storage/API names are intentionally kept stable; frontend copy remains
 * neutral and non-gamified.
 */

import { api } from './client';

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
  /** Restrict before the row cap to insights containing every structured signal. */
  pairSignals?: readonly { kind: string; id: string }[];
}

export type TagCooccurrenceRange = '7d' | '30d' | '90d' | '1y';

export interface TagCooccurrenceTagRef {
  tag_id: string;
  slug: string;
  name: string;
  category: string;
  color: string | null;
}

export interface TagCooccurrencePair {
  tag_a: TagCooccurrenceTagRef;
  tag_b: TagCooccurrenceTagRef;
  count: number;
  pct_of_a: number;
  pct_of_b: number;
}

export interface TagCooccurrenceResponse {
  range: TagCooccurrenceRange;
  start_date: string;
  end_date: string;
  min_count: number;
  pairs: TagCooccurrencePair[];
  /**
   * The window holds fewer logged days than the analysis needs. An empty
   * `pairs` then means "cannot be computed here", not "nothing found" — a 7-day
   * range can never reach the floor (#966).
   */
  window_too_short?: boolean;
}

export interface TagCooccurrenceQuery {
  range?: TagCooccurrenceRange;
  min_count?: number;
}

export interface TagClusterMember {
  kind: 'tag' | 'symptom';
  signal_id: string;
  slug: string;
  name: string;
  icon?: string | null;
  category?: string | null;
  color?: string | null;
}

export interface TagClusterGroup {
  cluster_id: number;
  label: string;
  tags: TagCooccurrenceTagRef[];
  members: TagClusterMember[];
  cluster_kind: 'tags_only' | 'mixed';
  strength: number;
}

export interface TagClustersResponse {
  status: 'ok' | 'insufficient_data';
  entry_count: number;
  active_tag_count: number;
  active_signal_count: number;
  window_days: number;
  k: number | null;
  reason: string | null;
  cluster_kind: 'tags_only' | 'mixed';
  cluster_maturity?: 'early' | 'provisional' | 'robust' | null;
  cluster_mode?: 'pair' | 'kmeans' | null;
  entries_until_robust?: number | null;
  silhouette_score?: number | null;
  clusters: TagClusterGroup[];
  /** #706: transparency + client-side strength bands (defaulted for old backends). */
  shown_cluster_count?: number;
  omitted_signal_count?: number;
  strength_floor?: number;
}

export interface InsightRegenerateResponse {
  status: 'ok';
  generated_for_date: string;
  insight_count: number;
  tag_clusters_status: 'ok' | 'insufficient_data';
  trigger_source: string;
}

export interface SymptomTagCooccurrenceSymptomRef {
  symptom_id: string;
  slug: string;
  name: string;
  icon: string | null;
}

export type SymptomTagCooccurrenceConfounder = 'weekday' | 'work_context' | 'calendar_context';

export interface SymptomTagCooccurrenceCell {
  symptom: SymptomTagCooccurrenceSymptomRef;
  tag: TagCooccurrenceTagRef;
  phi: number;
  jaccard: number;
  lift: number;
  co_count: number;
  symptom_count: number;
  tag_count: number;
  total_count: number;
  p_value_corrected: number;
  confounder: SymptomTagCooccurrenceConfounder | null;
}

export interface SymptomTagCooccurrenceResponse {
  range: TagCooccurrenceRange;
  start_date: string;
  end_date: string;
  min_count: number;
  cells: SymptomTagCooccurrenceCell[];
}

function buildQuery(query: InsightListQuery): string {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Separate builder rather than a branch in `buildQuery`: `/insights` physically
 * cannot emit `insight_type` this way, instead of merely being typed not to.
 */
function buildLatestQuery(query: LatestInsightListQuery): string {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  // Repeated `insight_type=` params — FastAPI reads them as a list.
  for (const type of query.insightTypes ?? []) params.append('insight_type', type);
  for (const signal of query.pairSignals ?? []) {
    params.append('pair_signal', `${signal.kind}:${signal.id}`);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

/** GET /insights/latest - list latest generated insights by analytical subject. */
export async function listLatestInsights(
  query: LatestInsightListQuery = {}
): Promise<InsightListResponse> {
  return api.get<InsightListResponse>(`/insights/latest${buildLatestQuery(query)}`);
}

/** GET /insights - chronological insight history (newest-first, no subject dedupe). */
export async function listInsights(query: InsightListQuery = {}): Promise<InsightListResponse> {
  return api.get<InsightListResponse>(`/insights${buildQuery(query)}`);
}

/** GET /insights/tag-cooccurrence - tag pair counts for the co-occurrence heatmap (M5.1). */
export async function fetchTagCooccurrence(
  query: TagCooccurrenceQuery = {}
): Promise<TagCooccurrenceResponse> {
  const params = new URLSearchParams();
  if (query.range) params.set('range', query.range);
  if (query.min_count !== undefined) params.set('min_count', String(query.min_count));
  const qs = params.toString();
  return api.get<TagCooccurrenceResponse>(
    qs ? `/insights/tag-cooccurrence?${qs}` : '/insights/tag-cooccurrence'
  );
}

/** GET /insights/tag-clusters - M7 tag groups that often appear together. */
export async function fetchTagClusters(): Promise<TagClustersResponse> {
  return api.get<TagClustersResponse>('/insights/tag-clusters');
}

/** GET /insights/symptom-tag-cooccurrence - symptom x tag lift cells for M7. */
export async function fetchSymptomTagCooccurrence(
  query: TagCooccurrenceQuery = {}
): Promise<SymptomTagCooccurrenceResponse> {
  const params = new URLSearchParams();
  if (query.range) params.set('range', query.range);
  if (query.min_count !== undefined) params.set('min_count', String(query.min_count));
  const qs = params.toString();
  return api.get<SymptomTagCooccurrenceResponse>(
    qs ? `/insights/symptom-tag-cooccurrence?${qs}` : '/insights/symptom-tag-cooccurrence'
  );
}

export interface InsightEventWindowResponse {
  onset: string;
  label: string | null;
}

export interface InsightEventWindowsResponse {
  range: TagCooccurrenceRange;
  start_date: string;
  end_date: string;
  events: InsightEventWindowResponse[];
  points: import('./stats').TimeseriesPoint[];
  /** #488: lag insights align on the feature; the outcome is expected at +lag_days. */
  lag_days?: number | null;
}

/** POST /insights/regenerate — on-demand insight + tag-cluster regeneration (M10.1). */
export async function regenerateInsights(): Promise<InsightRegenerateResponse> {
  return api.post<InsightRegenerateResponse>('/insights/regenerate');
}

/** GET /insights/{id}/event-windows — ADR-0035 §6 explore-events data. */
export async function fetchInsightEventWindows(
  insightId: string,
  range: TagCooccurrenceRange,
  options?: { signal?: AbortSignal }
): Promise<InsightEventWindowsResponse> {
  const params = new URLSearchParams({ range });
  const path = `/insights/${encodeURIComponent(insightId)}/event-windows?${params}`;
  return options
    ? api.get<InsightEventWindowsResponse>(path, options)
    : api.get<InsightEventWindowsResponse>(path);
}

/** GET /insights/{id} — single insight for Layer-2 signal detail. */
export async function fetchInsight(
  insightId: string,
  options?: { signal?: AbortSignal }
): Promise<InsightResponse> {
  const path = `/insights/${encodeURIComponent(insightId)}`;
  return options ? api.get<InsightResponse>(path, options) : api.get<InsightResponse>(path);
}

export interface InsightVerificationPoint {
  date: string;
  value: number;
  present: boolean;
}

export interface InsightVerificationResponse {
  range: TagCooccurrenceRange;
  start_date: string;
  end_date: string;
  metric: string;
  subject_label: string | null;
  points: InsightVerificationPoint[];
  with_mean: number | null;
  without_mean: number | null;
  with_se: number | null;
  without_se: number | null;
  with_n: number;
  without_n: number;
}

/** GET /insights/{id}/verification — with/without day series (Phase 7 / G1). */
export async function fetchInsightVerification(
  insightId: string,
  range: TagCooccurrenceRange = '90d',
  options?: { signal?: AbortSignal }
): Promise<InsightVerificationResponse> {
  const params = new URLSearchParams({ range });
  const path = `/insights/${encodeURIComponent(insightId)}/verification?${params}`;
  return options
    ? api.get<InsightVerificationResponse>(path, options)
    : api.get<InsightVerificationResponse>(path);
}

export async function fetchLatestInsightDigest(): Promise<InsightDigestResponse> {
  return api.get<InsightDigestResponse>('/insights/digest/latest');
}

export type InsightHistoryVisibility = 'active' | 'dismissed' | 'all';

export interface InsightHistoryItem extends InsightResponse {
  visibility: 'active' | 'dismissed';
  subject_key: string;
  first_seen_on: string | null;
  last_seen_on: string | null;
  observation_count: number | null;
}

export interface InsightHistoryResponse {
  insights: InsightHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface InsightHistoryQuery {
  status?: InsightHistoryVisibility;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

/** GET /insights/history — chronological timeline / archive (#601 Phase 2). */
export async function listInsightHistory(
  query: InsightHistoryQuery = {}
): Promise<InsightHistoryResponse> {
  const params = new URLSearchParams();
  if (query.status) params.set('status', query.status);
  if (query.from) params.set('from', query.from);
  if (query.to) params.set('to', query.to);
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  if (query.offset !== undefined) params.set('offset', String(query.offset));
  const qs = params.toString();
  return api.get<InsightHistoryResponse>(qs ? `/insights/history?${qs}` : '/insights/history');
}

export interface InsightDismissalResponse {
  id: string;
  subject_key: string;
  insight_id: string | null;
  dismissed_at: string;
  created_at: string;
  insight: InsightResponse | null;
}

export interface InsightDismissalListResponse {
  dismissals: InsightDismissalResponse[];
}

/** GET /insights/dismissals — subject-stable hidden insights. */
export async function listInsightDismissals(): Promise<InsightDismissalListResponse> {
  return api.get<InsightDismissalListResponse>('/insights/dismissals');
}

/** POST /insights/dismissals — hide by insight id (subject-stable). */
export async function createInsightDismissal(insightId: string): Promise<InsightDismissalResponse> {
  return api.post<InsightDismissalResponse>('/insights/dismissals', {
    insight_id: insightId,
  });
}

/** DELETE /insights/dismissals/{id} — undo hide. */
export async function deleteInsightDismissal(dismissalId: string): Promise<void> {
  await api.delete(`/insights/dismissals/${encodeURIComponent(dismissalId)}`);
}

/** DELETE /insights/dismissals/by-insight/{id} — undo by insight id. */
export async function deleteInsightDismissalByInsightId(insightId: string): Promise<void> {
  await api.delete(`/insights/dismissals/by-insight/${encodeURIComponent(insightId)}`);
}
