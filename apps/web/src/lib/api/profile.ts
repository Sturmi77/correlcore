import { api } from './client';

export type SleepHoursTypical = '5h' | '6h' | '7h' | '8h' | '9h_plus';
export type WorkContextTypical = 'office' | 'hybrid' | 'remote' | 'other';
export type SportFrequency = 'rarely' | '1_2_week' | '3_4_week' | 'daily';
export type InsightCuriosity = 'work_life' | 'energy_sleep' | 'habits_sport' | 'wellbeing';

export interface UserProfilePayload {
  sleep_hours_typical?: SleepHoursTypical | null;
  work_context_typical?: WorkContextTypical | null;
  sport_frequency?: SportFrequency | null;
  insight_curiosity?: InsightCuriosity | null;
}

export interface UserProfileResponse extends UserProfilePayload {
  user_id: string;
  created_at: string;
  updated_at: string;
}

export async function upsertUserProfile(payload: UserProfilePayload): Promise<UserProfileResponse> {
  return api.put<UserProfileResponse>('/user/profile', payload);
}
