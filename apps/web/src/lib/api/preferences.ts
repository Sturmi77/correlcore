import { api } from './client';

export interface UserPreferencesResponse {
  user_id: string;
  analytics_enabled: boolean;
  digest_enabled: boolean;
  onboarding_retro_completed: boolean;
  onboarding_profile_completed: boolean;
  onboarding_maturity_intro_seen: boolean;
  cycle_tracking_enabled: boolean;
  dismissed_insight_keys: string[];
  reached_milestone_keys: string[];
  last_seen_insight_at: string | null;
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
  dismissed_insight_keys?: string[];
  reached_milestone_keys?: string[];
  last_seen_insight_at?: string | null;
}

export async function fetchUserPreferences(): Promise<UserPreferencesResponse> {
  return api.get<UserPreferencesResponse>('/user/preferences');
}

export async function updateUserPreferences(
  payload: UserPreferencesUpdate
): Promise<UserPreferencesResponse> {
  return api.patch<UserPreferencesResponse>('/user/preferences', payload);
}
