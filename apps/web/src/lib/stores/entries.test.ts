/**
 * Tests for the entries store (Issue #7).
 *
 * The store is a thin in-memory cache around the entries API. We mock
 * the API module and assert state transitions + ordering invariants.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/entries', () => ({
  createEntry: vi.fn(),
  listEntries: vi.fn(),
}));

import * as entriesApi from '$lib/api/entries';
import { entries, entriesList, refreshEntries, resetEntriesStore, submitEntry } from './entries';

function makeEntry(overrides: Partial<entriesApi.EntryResponse> = {}): entriesApi.EntryResponse {
  return {
    id: 'e_' + Math.random().toString(36).slice(2, 8),
    user_id: 'u_1',
    entry_date: '2026-05-04',
    slot: 'day',
    mood_score: 3,
    energy: 3,
    stress: 3,
    work_context: 'homeoffice',
    source: 'direct',
    note: null,
    created_at: '2026-05-04T10:00:00Z',
    updated_at: '2026-05-04T10:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetEntriesStore();
  vi.clearAllMocks();
});

afterEach(() => {
  resetEntriesStore();
});

describe('refreshEntries', () => {
  it('starts in idle state', () => {
    expect(get(entries).status).toBe('idle');
  });

  it('transitions to ready after a successful list call', async () => {
    const list = [makeEntry({ id: 'a' }), makeEntry({ id: 'b' })];
    vi.mocked(entriesApi.listEntries).mockResolvedValueOnce(list);

    const result = await refreshEntries();

    expect(result).toHaveLength(2);
    const state = get(entries);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.entries).toEqual(list);
    }
    expect(get(entriesList)).toHaveLength(2);
  });

  it('transitions to error and rethrows on failure', async () => {
    vi.mocked(entriesApi.listEntries).mockRejectedValueOnce(new Error('boom'));

    await expect(refreshEntries()).rejects.toThrow('boom');

    const state = get(entries);
    expect(state.status).toBe('error');
    if (state.status === 'error') {
      expect(state.message).toBe('boom');
    }
  });

  it('forwards the limit to the API', async () => {
    vi.mocked(entriesApi.listEntries).mockResolvedValueOnce([]);
    await refreshEntries(7);
    expect(entriesApi.listEntries).toHaveBeenCalledWith({ limit: 7 });
  });
});

describe('submitEntry', () => {
  it('prepends the new entry on top of the cache', async () => {
    const existing = makeEntry({ id: 'old' });
    vi.mocked(entriesApi.listEntries).mockResolvedValueOnce([existing]);
    await refreshEntries();

    const created = makeEntry({ id: 'new' });
    vi.mocked(entriesApi.createEntry).mockResolvedValueOnce(created);

    const out = await submitEntry({
      entry_date: '2026-05-04',
      mood_score: 4,
      energy: 4,
      stress: 2,
      work_context: 'office',
    });

    expect(out).toEqual(created);
    const list = get(entriesList);
    expect(list).toHaveLength(2);
    expect(list[0].id).toBe('new');
    expect(list[1].id).toBe('old');
  });

  it('seeds the cache when the store was idle', async () => {
    const created = makeEntry({ id: 'first' });
    vi.mocked(entriesApi.createEntry).mockResolvedValueOnce(created);

    await submitEntry({
      entry_date: '2026-05-04',
      mood_score: 3,
      energy: 3,
      stress: 3,
      work_context: 'homeoffice',
    });

    const list = get(entriesList);
    expect(list).toHaveLength(1);
    expect(list[0].id).toBe('first');
  });

  it('does not mutate the cache on API failure', async () => {
    const existing = makeEntry({ id: 'old' });
    vi.mocked(entriesApi.listEntries).mockResolvedValueOnce([existing]);
    await refreshEntries();

    vi.mocked(entriesApi.createEntry).mockRejectedValueOnce(new Error('409'));

    await expect(
      submitEntry({
        entry_date: '2026-05-04',
        mood_score: 3,
        energy: 3,
        stress: 3,
        work_context: 'homeoffice',
      })
    ).rejects.toThrow('409');

    const list = get(entriesList);
    expect(list).toHaveLength(1);
    expect(list[0].id).toBe('old');
  });
});
