/**
 * Tests for the tags API client (Issue #8).
 *
 * The underlying `api` helper is mocked so the assertions are about
 * the call shape (path + body) the client emits — same pattern as
 * entries.test.ts.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

import { api } from './client';
import {
  assignTagsToEntry,
  createTag,
  deleteTag,
  listDefaultTags,
  listTagsForEntry,
  listVisibleTags,
  updateTag,
} from './tags';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('listDefaultTags', () => {
  it('GETs /tags/default', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listDefaultTags();
    expect(api.get).toHaveBeenCalledWith('/tags/default');
  });
});

describe('listVisibleTags', () => {
  it('GETs /tags', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listVisibleTags();
    expect(api.get).toHaveBeenCalledWith('/tags');
  });

  it('GETs /tags with include_hidden when requested', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listVisibleTags({ include_hidden: true });
    expect(api.get).toHaveBeenCalledWith('/tags?include_hidden=true');
  });
});

describe('createTag', () => {
  it('POSTs to /tags with the payload', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ id: 't1' });
    await createTag({
      slug: 'yoga',
      name: 'Yoga',
      category: 'sport',
      icon: '🧘',
      color: '#a1b2c3',
    });
    expect(api.post).toHaveBeenCalledWith('/tags', {
      slug: 'yoga',
      name: 'Yoga',
      category: 'sport',
      icon: '🧘',
      color: '#a1b2c3',
    });
  });
});

describe('updateTag', () => {
  it('PATCHes /tags/{id}', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ id: 't1' });
    await updateTag('t1', { name: 'Renamed', is_hidden: true });
    expect(api.patch).toHaveBeenCalledWith('/tags/t1', { name: 'Renamed', is_hidden: true });
  });
});

describe('deleteTag', () => {
  it('DELETEs /tags/{id}', async () => {
    vi.mocked(api.delete).mockResolvedValueOnce(undefined);
    await deleteTag('t1');
    expect(api.delete).toHaveBeenCalledWith('/tags/t1');
  });
});

describe('listTagsForEntry', () => {
  it('GETs /entries/{id}/tags', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listTagsForEntry('e1');
    expect(api.get).toHaveBeenCalledWith('/entries/e1/tags');
  });
});

describe('assignTagsToEntry', () => {
  it('PUTs the full tag_ids list to /entries/{id}/tags', async () => {
    vi.mocked(api.put).mockResolvedValueOnce([]);
    await assignTagsToEntry('e1', ['t1', 't2']);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/tags', {
      tag_ids: ['t1', 't2'],
    });
  });

  it('sends an empty list to clear all tags', async () => {
    vi.mocked(api.put).mockResolvedValueOnce([]);
    await assignTagsToEntry('e1', []);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/tags', { tag_ids: [] });
  });
});
