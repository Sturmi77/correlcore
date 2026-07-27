import { api } from './client';
import type { HabitType, TagCategory, TagResponse } from './tags';

export interface TagSuggestion {
  slug: string;
  name: string;
  category: TagCategory;
  icon: string | null;
  color: string | null;
}

export interface TagSuggestionGroup {
  category: TagCategory;
  suggestions: TagSuggestion[];
}

export interface TagSuggestionsResponse {
  groups: TagSuggestionGroup[];
}

export interface OnboardingTagInput {
  slug?: string;
  name: string;
  category: TagCategory;
  icon?: string | null;
  color?: string | null;
  /** Optional habit facet (#564): build/reduce + weekly target (1–7). */
  habit_type?: HabitType;
  target_frequency?: number | null;
}

export interface OnboardingCompleteResponse {
  created_tags: TagResponse[];
  onboarding_retro_completed: boolean;
  onboarding_profile_completed: boolean;
}

export function fetchTagSuggestions(): Promise<TagSuggestionsResponse> {
  return api.get<TagSuggestionsResponse>('/onboarding/tag-suggestions');
}

export function completeOnboarding(
  tags: OnboardingTagInput[]
): Promise<OnboardingCompleteResponse> {
  return api.post<OnboardingCompleteResponse>('/onboarding/complete', { tags });
}
