/**
 * Tags API client — Issue #8.
 *
 * Mirrors backend/app/schemas/tag.py. All calls go through `apiFetch`,
 * which adds `credentials: 'include'` and handles single-flight refresh
 * on 401 (see ./client.ts).
 *
 * The tag system has two surfaces:
 *   1. Tag CRUD — defaults plus user-owned custom/override tags.
 *   2. Entry-tag assignment — replace-set semantics on
 *      PUT /entries/{id}/tags.
 */

import { api } from './client';

// ---------------------------------------------------------------------------
// Enums — keep in sync with app/models/tag.py (TagCategory)
// ---------------------------------------------------------------------------

export type TagCategory =
  | 'sport'
  | 'social'
  | 'work'
  | 'leisure'
  | 'consumption'
  | 'health'
  | 'other';

export const TAG_CATEGORIES: readonly TagCategory[] = [
  'sport',
  'social',
  'work',
  'leisure',
  'consumption',
  'health',
  'other',
] as const;

/** Hard upper bound — kept in sync with MAX_TAGS_PER_ENTRY in tag.py. */
export const MAX_TAGS_PER_ENTRY = 50;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export interface TagResponse {
  id: string;
  user_id: string | null;
  slug: string;
  name: string;
  category: TagCategory;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  is_hidden: boolean;
  created_at: string;
  updated_at: string;
}

export interface TagCreatePayload {
  slug: string;
  name: string;
  category: TagCategory;
  icon?: string | null;
  color?: string | null;
}

export interface TagUpdatePayload {
  name?: string;
  category?: TagCategory;
  icon?: string | null;
  color?: string | null;
  is_hidden?: boolean;
}

export interface TagListQuery {
  include_hidden?: boolean;
}

// ---------------------------------------------------------------------------
// Calls — Tag CRUD
// ---------------------------------------------------------------------------

/** GET /tags/default — public list of curated default tags (no auth). */
export async function listDefaultTags(): Promise<TagResponse[]> {
  return api.get<TagResponse[]>('/tags/default');
}

/** GET /tags — defaults + the current user's custom tags. */
export async function listVisibleTags(query: TagListQuery = {}): Promise<TagResponse[]> {
  const params = new URLSearchParams();
  if (query.include_hidden) params.set('include_hidden', 'true');
  const qs = params.toString();
  return api.get<TagResponse[]>(qs ? `/tags?${qs}` : '/tags');
}

/** POST /tags — create a custom tag for the current user. */
export async function createTag(payload: TagCreatePayload): Promise<TagResponse> {
  return api.post<TagResponse>('/tags', payload);
}

/** PATCH /tags/{id} — update a custom tag or create/update a default override. */
export async function updateTag(id: string, payload: TagUpdatePayload): Promise<TagResponse> {
  return api.patch<TagResponse>(`/tags/${id}`, payload);
}

/** DELETE /tags/{id} — delete a custom tag (cascades to entry_tags). */
export async function deleteTag(id: string): Promise<void> {
  await api.delete(`/tags/${id}`);
}

// ---------------------------------------------------------------------------
// Calls — Entry-tag assignment
// ---------------------------------------------------------------------------

/** GET /entries/{id}/tags — current tag set on an entry. */
export async function listTagsForEntry(entryId: string): Promise<TagResponse[]> {
  return api.get<TagResponse[]>(`/entries/${entryId}/tags`);
}

/**
 * PUT /entries/{id}/tags — replace the entry's full tag set.
 *
 * Replace-set semantics: pass the complete desired list. Sending an
 * empty array clears all tags on the entry.
 */
export async function assignTagsToEntry(entryId: string, tagIds: string[]): Promise<TagResponse[]> {
  return api.put<TagResponse[]>(`/entries/${entryId}/tags`, { tag_ids: tagIds });
}
