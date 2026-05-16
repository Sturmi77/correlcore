/**
 * Tests for the tags store (Issue #8).
 *
 * Mirrors the entries store tests: the API module is mocked and we
 * assert state transitions plus the grouping derived store.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/tags', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/tags')>('$lib/api/tags');
  return {
    ...actual,
    listVisibleTags: vi.fn(),
    createTag: vi.fn(),
    updateTag: vi.fn(),
    deleteTag: vi.fn(),
  };
});

import * as tagsApi from '$lib/api/tags';
import {
  patchTag,
  refreshTags,
  removeTag,
  resetTagsStore,
  submitTag,
  tags,
  tagsByCategory,
  tagsList,
} from './tags';

function makeTag(overrides: Partial<tagsApi.TagResponse> = {}): tagsApi.TagResponse {
  return {
    id: 't_' + Math.random().toString(36).slice(2, 8),
    user_id: null,
    slug: 'sample',
    name: 'Sample',
    category: 'other',
    icon: null,
    color: null,
    is_default: true,
    is_hidden: false,
    created_at: '2026-05-04T10:00:00Z',
    updated_at: '2026-05-04T10:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetTagsStore();
  vi.clearAllMocks();
});

afterEach(() => {
  resetTagsStore();
});

describe('refreshTags', () => {
  it('starts in idle state', () => {
    expect(get(tags).status).toBe('idle');
  });

  it('transitions to ready after a successful list call', async () => {
    const list = [makeTag({ id: 'a', name: 'Aa' }), makeTag({ id: 'b', name: 'Bb' })];
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce(list);

    const result = await refreshTags();

    expect(result).toHaveLength(2);
    const state = get(tags);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.tags).toEqual(list);
    }
    expect(get(tagsList)).toHaveLength(2);
  });

  it('transitions to error and rethrows on failure', async () => {
    vi.mocked(tagsApi.listVisibleTags).mockRejectedValueOnce(new Error('boom'));

    await expect(refreshTags()).rejects.toThrow('boom');

    const state = get(tags);
    expect(state.status).toBe('error');
    if (state.status === 'error') {
      expect(state.message).toBe('boom');
    }
  });
});

describe('submitTag', () => {
  it('appends the new tag to the cache', async () => {
    const existing = makeTag({ id: 'old', name: 'Old' });
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce([existing]);
    await refreshTags();

    const created = makeTag({ id: 'new', name: 'New', is_default: false });
    vi.mocked(tagsApi.createTag).mockResolvedValueOnce(created);

    const out = await submitTag({
      slug: 'new',
      name: 'New',
      category: 'other',
    });

    expect(out).toEqual(created);
    const list = get(tagsList);
    expect(list).toHaveLength(2);
    expect(list.map((t) => t.id)).toContain('new');
    expect(list.map((t) => t.id)).toContain('old');
  });

  it('seeds the cache when the store was idle', async () => {
    const created = makeTag({ id: 'first', is_default: false });
    vi.mocked(tagsApi.createTag).mockResolvedValueOnce(created);

    await submitTag({ slug: 'first', name: 'First', category: 'other' });

    const list = get(tagsList);
    expect(list).toHaveLength(1);
    expect(list[0].id).toBe('first');
  });
});

describe('patchTag', () => {
  it('replaces the matching tag in place', async () => {
    const existing = makeTag({ id: 't1', name: 'Old', is_default: false });
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce([existing]);
    await refreshTags();

    const updated = { ...existing, name: 'New' };
    vi.mocked(tagsApi.updateTag).mockResolvedValueOnce(updated);

    await patchTag('t1', { name: 'New' });

    const list = get(tagsList);
    expect(list).toHaveLength(1);
    expect(list[0].name).toBe('New');
  });

  it('drops a tag from the cache when an update hides it', async () => {
    const existing = makeTag({ id: 't1', name: 'Old', is_default: false });
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce([existing]);
    await refreshTags();

    vi.mocked(tagsApi.updateTag).mockResolvedValueOnce({ ...existing, is_hidden: true });

    await patchTag('t1', { is_hidden: true });

    expect(get(tagsList)).toHaveLength(0);
  });
});

describe('removeTag', () => {
  it('removes the tag from the cache', async () => {
    const existing = makeTag({ id: 't1', is_default: false });
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce([existing]);
    await refreshTags();

    vi.mocked(tagsApi.deleteTag).mockResolvedValueOnce(undefined);

    await removeTag('t1');

    expect(get(tagsList)).toHaveLength(0);
  });
});

describe('tagsByCategory', () => {
  it('groups by category and sorts alphabetically within each group', async () => {
    const list = [
      makeTag({ id: '1', name: 'Zumba', category: 'sport' }),
      makeTag({ id: '2', name: 'Aerobic', category: 'sport' }),
      makeTag({ id: '3', name: 'Coffee', category: 'consumption' }),
    ];
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce(list);
    await refreshTags();

    const grouped = get(tagsByCategory);
    expect(grouped.sport.map((t) => t.name)).toEqual(['Aerobic', 'Zumba']);
    expect(grouped.consumption.map((t) => t.name)).toEqual(['Coffee']);
    expect(grouped.work).toEqual([]);
    expect(grouped.health).toEqual([]);
  });

  it('returns empty groups when the store is idle', () => {
    const grouped = get(tagsByCategory);
    expect(grouped.sport).toEqual([]);
    expect(grouped.other).toEqual([]);
  });

  it('does not expose hidden tags in picker groups', async () => {
    const list = [
      makeTag({ id: 'visible', name: 'Visible', category: 'sport' }),
      makeTag({ id: 'hidden', name: 'Hidden', category: 'sport', is_hidden: true }),
    ];
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce(list);
    await refreshTags();

    const grouped = get(tagsByCategory);
    expect(grouped.sport.map((t) => t.id)).toEqual(['visible']);
  });
});
