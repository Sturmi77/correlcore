/**
 * Tags store — Issue #8.
 *
 * In-memory cache of the tag catalogue (defaults + custom tags). The
 * tag list is small (≤ a few dozen) and doesn't change often, so we
 * keep one flat array in memory and refresh on demand. The picker
 * groups tags by category at the view layer.
 *
 * State shape mirrors the entries store: `idle | loading | ready | error`.
 */

import { writable, derived, get } from 'svelte/store';
import {
  createTag as apiCreateTag,
  deleteTag as apiDeleteTag,
  listVisibleTags as apiListVisibleTags,
  updateTag as apiUpdateTag,
  type TagCategory,
  type TagCreatePayload,
  type TagResponse,
  type TagUpdatePayload,
} from '$lib/api/tags';

export type TagsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; tags: TagResponse[] }
  | { status: 'error'; message: string };

const _tags = writable<TagsState>({ status: 'idle' });

export const tags = { subscribe: _tags.subscribe };

/** Flat list of currently-known tags (defaults + custom), or [] when not ready. */
export const tagsList = derived(_tags, ($s) => ($s.status === 'ready' ? $s.tags : []));

/** Tags grouped by category for picker rendering. Stable category order. */
export const tagsByCategory = derived(_tags, ($s) => {
  const grouped: Record<TagCategory, TagResponse[]> = {
    sport: [],
    social: [],
    work: [],
    leisure: [],
    consumption: [],
    health: [],
    cycle: [],
    other: [],
  };
  if ($s.status !== 'ready') return grouped;
  for (const tag of $s.tags) {
    if (tag.is_hidden) continue;
    grouped[tag.category].push(tag);
  }
  // Sort each category alphabetically by display name (locale-aware) so the
  // picker is stable across reloads regardless of insert order.
  for (const cat of Object.keys(grouped) as TagCategory[]) {
    grouped[cat].sort((a, b) => a.name.localeCompare(b.name));
  }
  return grouped;
});

/** Refresh the tag catalogue from the server. */
export async function refreshTags(): Promise<TagResponse[]> {
  _tags.set({ status: 'loading' });
  try {
    const list = await apiListVisibleTags();
    _tags.set({ status: 'ready', tags: list });
    return list;
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load tags';
    _tags.set({ status: 'error', message });
    throw err;
  }
}

/** Create a custom tag and add it to the cache. */
export async function submitTag(payload: TagCreatePayload): Promise<TagResponse> {
  const created = await apiCreateTag(payload);
  const current = get(_tags);
  const existing = current.status === 'ready' ? current.tags : [];
  _tags.set({ status: 'ready', tags: [...existing, created] });
  return created;
}

/** Update a tag in place in the cache. Default edits may return a user override. */
export async function patchTag(id: string, payload: TagUpdatePayload): Promise<TagResponse> {
  const updated = await apiUpdateTag(id, payload);
  const current = get(_tags);
  if (current.status === 'ready') {
    _tags.set({
      status: 'ready',
      tags: current.tags
        .filter((t) => t.id !== id)
        .concat(updated)
        .filter((t) => !t.is_hidden),
    });
  }
  return updated;
}

/** Delete a custom tag and remove it from the cache. */
export async function removeTag(id: string): Promise<void> {
  await apiDeleteTag(id);
  const current = get(_tags);
  if (current.status === 'ready') {
    _tags.set({
      status: 'ready',
      tags: current.tags.filter((t) => t.id !== id),
    });
  }
}

/** Reset the cache — useful on logout. */
export function resetTagsStore(): void {
  _tags.set({ status: 'idle' });
}
