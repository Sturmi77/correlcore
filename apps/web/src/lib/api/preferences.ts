import { api } from './client';

export type HomeSectionKey =
  'first_week_banner' | 'daily_brief' | 'work_context' | 'weekday_overview';

export interface HomeSectionPreference {
  key: HomeSectionKey;
  enabled: boolean;
}

export type InsightSectionKey =
  | 'correlation_matrix'
  | 'insight_feed'
  | 'lag_heatmap'
  | 'dismissed'
  | 'symptom_analytics'
  | 'tag_groups'
  | 'tag_cooccurrence';

export interface InsightSectionPreference {
  key: InsightSectionKey;
  enabled: boolean;
}

export interface UserPreferencesResponse {
  user_id: string;
  analytics_enabled: boolean;
  digest_enabled: boolean;
  onboarding_retro_completed: boolean;
  onboarding_profile_completed: boolean;
  onboarding_maturity_intro_seen: boolean;
  cycle_tracking_enabled: boolean;
  // Additive (M8 Sprint 4): older mocks/fallbacks may omit it — treat as true.
  health_connect_sync_sleep_enabled?: boolean;
  dismissed_insight_keys: string[];
  reached_milestone_keys: string[];
  last_seen_insight_at: string | null;
  // #739: newest weekly digest the user has seen in the one-time modal.
  last_seen_digest_at?: string | null;
  home_sections?: HomeSectionPreference[] | null;
  insight_sections?: InsightSectionPreference[] | null;
  created_at: string;
  updated_at: string;
}

export interface UserPreferencesUpdate {
  analytics_enabled?: boolean;
  digest_enabled?: boolean;
  onboarding_retro_completed?: boolean;
  onboarding_profile_completed?: boolean;
  onboarding_maturity_intro_seen?: boolean;
  cycle_tracking_enabled?: boolean;
  health_connect_sync_sleep_enabled?: boolean;
  dismissed_insight_keys?: string[];
  reached_milestone_keys?: string[];
  last_seen_insight_at?: string | null;
  last_seen_digest_at?: string | null;
  home_sections?: HomeSectionPreference[];
  insight_sections?: InsightSectionPreference[];
}

export async function fetchUserPreferences(): Promise<UserPreferencesResponse> {
  return api.get<UserPreferencesResponse>('/user/preferences');
}

export async function updateUserPreferences(
  payload: UserPreferencesUpdate
): Promise<UserPreferencesResponse> {
  return api.patch<UserPreferencesResponse>('/user/preferences', payload);
}
