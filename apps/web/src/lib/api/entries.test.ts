/**
 * Tests for the entries API client (Issue #7).
 *
 * We mock the underlying `api` helper exported from ./client so the
 * tests stay free of any HTTP machinery — the assertion is the call
 * shape (path + body) the API module sends.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

import { api } from './client';
import { createEntry, fetchEntry, listEntries, updateEntry } from './entries';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('createEntry', () => {
  it('POSTs to /entries with the payload', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ id: 'e1' });
    await createEntry({
      entry_date: '2026-05-04',
      mood_score: 4,
      energy: 3,
      stress: 2,
      work_context: 'homeoffice',
      note: 'hi',
    });
    expect(api.post).toHaveBeenCalledWith(
      '/entries',
      expect.objectContaining({
        entry_date: '2026-05-04',
        mood_score: 4,
        note: 'hi',
      })
    );
  });
});

describe('fetchEntry', () => {
  it('GETs /entries/{id}', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ id: 'e1' });
    await fetchEntry('e1');
    expect(api.get).toHaveBeenCalledWith('/entries/e1');
  });
});

describe('listEntries', () => {
  it('GETs /entries with no query when filters are empty', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listEntries();
    expect(api.get).toHaveBeenCalledWith('/entries');
  });

  it('appends start_date, end_date, and limit', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listEntries({ start_date: '2026-05-01', end_date: '2026-05-04', limit: 30 });
    const path = vi.mocked(api.get).mock.calls[0][0] as string;
    expect(path.startsWith('/entries?')).toBe(true);
    expect(path).toContain('start_date=2026-05-01');
    expect(path).toContain('end_date=2026-05-04');
    expect(path).toContain('limit=30');
  });
});

describe('updateEntry', () => {
  it('PATCHes /entries/{id}', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ id: 'e1' });
    await updateEntry('e1', { mood_score: 5 });
    expect(api.patch).toHaveBeenCalledWith('/entries/e1', { mood_score: 5 });
  });
});
