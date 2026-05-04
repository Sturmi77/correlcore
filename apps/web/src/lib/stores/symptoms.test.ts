/**
 * Tests for the symptoms store (Issue #9 + Issue #57 Custom-Symptome).
 *
 * Mirrors the tags store tests: the API module is mocked and we assert
 * state transitions plus the derived sorted list.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/symptoms', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/symptoms')>('$lib/api/symptoms');
  return {
    ...actual,
    listVisibleSymptoms: vi.fn(),
    createSymptom: vi.fn(),
    updateSymptom: vi.fn(),
    deleteSymptom: vi.fn(),
  };
});

import * as symptomsApi from '$lib/api/symptoms';
import {
  patchSymptom,
  refreshSymptoms,
  removeSymptom,
  resetSymptomsStore,
  submitSymptom,
  symptoms,
  symptomsList,
} from './symptoms';

function makeSymptom(
  overrides: Partial<symptomsApi.SymptomResponse> = {}
): symptomsApi.SymptomResponse {
  return {
    id: 's_' + Math.random().toString(36).slice(2, 8),
    user_id: null,
    slug: 'sample',
    name: 'Sample',
    icon: null,
    is_default: true,
    created_at: '2026-05-04T10:00:00Z',
    updated_at: '2026-05-04T10:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetSymptomsStore();
  vi.clearAllMocks();
});

afterEach(() => {
  resetSymptomsStore();
});

describe('refreshSymptoms', () => {
  it('starts in idle state', () => {
    expect(get(symptoms).status).toBe('idle');
  });

  it('transitions to ready after a successful list call', async () => {
    const list = [makeSymptom({ id: 'a', name: 'Aa' }), makeSymptom({ id: 'b', name: 'Bb' })];
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValueOnce(list);

    const result = await refreshSymptoms();

    expect(result).toHaveLength(2);
    const state = get(symptoms);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.symptoms).toEqual(list);
    }
    expect(get(symptomsList)).toHaveLength(2);
  });

  it('transitions to error and rethrows on failure', async () => {
    vi.mocked(symptomsApi.listVisibleSymptoms).mockRejectedValueOnce(new Error('boom'));

    await expect(refreshSymptoms()).rejects.toThrow('boom');

    const state = get(symptoms);
    expect(state.status).toBe('error');
    if (state.status === 'error') {
      expect(state.message).toBe('boom');
    }
  });
});

describe('symptomsList ordering', () => {
  it('puts defaults before custom and sorts each group alphabetically', async () => {
    const list = [
      makeSymptom({ id: 'd2', name: 'Zopf-Standard', is_default: true, slug: 'zopf' }),
      makeSymptom({ id: 'd1', name: 'Aspirin-Standard', is_default: true, slug: 'aspirin' }),
      makeSymptom({ id: 'c2', name: 'Zonk-Custom', is_default: false, slug: 'zonk' }),
      makeSymptom({
        id: 'c1',
        name: 'Aha-Custom',
        is_default: false,
        slug: 'aha',
        user_id: 'u1',
      }),
    ];
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValueOnce(list);
    await refreshSymptoms();

    const sorted = get(symptomsList);
    expect(sorted.map((s) => s.id)).toEqual(['d1', 'd2', 'c1', 'c2']);
  });

  it('returns an empty list when the store is idle', () => {
    expect(get(symptomsList)).toEqual([]);
  });
});

describe('submitSymptom', () => {
  it('appends the new symptom to the cache', async () => {
    const existing = makeSymptom({ id: 'old', name: 'Old', is_default: true });
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValueOnce([existing]);
    await refreshSymptoms();

    const created = makeSymptom({
      id: 'new',
      name: 'Migräne',
      is_default: false,
      slug: 'migraene',
      user_id: 'u1',
    });
    vi.mocked(symptomsApi.createSymptom).mockResolvedValueOnce(created);

    const out = await submitSymptom({ slug: 'migraene', name: 'Migräne' });

    expect(out).toEqual(created);
    const state = get(symptoms);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.symptoms).toHaveLength(2);
      expect(state.symptoms.map((s) => s.id)).toContain('new');
    }
  });

  it('seeds the cache when the store was idle', async () => {
    const created = makeSymptom({ id: 'first', is_default: false, user_id: 'u1' });
    vi.mocked(symptomsApi.createSymptom).mockResolvedValueOnce(created);

    await submitSymptom({ slug: 'first', name: 'First' });

    const state = get(symptoms);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.symptoms).toHaveLength(1);
      expect(state.symptoms[0].id).toBe('first');
    }
  });
});

describe('patchSymptom', () => {
  it('replaces the matching symptom in place', async () => {
    const existing = makeSymptom({
      id: 's1',
      name: 'Old',
      is_default: false,
      user_id: 'u1',
    });
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValueOnce([existing]);
    await refreshSymptoms();

    const updated = { ...existing, name: 'New' };
    vi.mocked(symptomsApi.updateSymptom).mockResolvedValueOnce(updated);

    await patchSymptom('s1', { name: 'New' });

    const state = get(symptoms);
    if (state.status === 'ready') {
      expect(state.symptoms).toHaveLength(1);
      expect(state.symptoms[0].name).toBe('New');
    }
  });
});

describe('removeSymptom', () => {
  it('removes the symptom from the cache', async () => {
    const existing = makeSymptom({ id: 's1', is_default: false, user_id: 'u1' });
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValueOnce([existing]);
    await refreshSymptoms();

    vi.mocked(symptomsApi.deleteSymptom).mockResolvedValueOnce(undefined);

    await removeSymptom('s1');

    const state = get(symptoms);
    if (state.status === 'ready') {
      expect(state.symptoms).toHaveLength(0);
    }
  });
});
