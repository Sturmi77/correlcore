/**
 * Tests for the symptom-catalogue store (Issue #9).
 *
 * The underlying API client is mocked so we only exercise the store
 * state transitions: idle → loading → ready, and the local-fallback
 * behaviour on fetch failure.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/symptoms', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/symptoms')>('$lib/api/symptoms');
  return {
    ...actual,
    listStandardSymptomKeys: vi.fn(),
  };
});

import { listStandardSymptomKeys } from '$lib/api/symptoms';
import {
  refreshSymptomCatalogue,
  resetSymptomsStore,
  symptomCatalogue,
  symptomKeysList,
} from './symptoms';

beforeEach(() => {
  vi.clearAllMocks();
  resetSymptomsStore();
});

describe('symptomCatalogue', () => {
  it('starts idle', () => {
    expect(get(symptomCatalogue).status).toBe('idle');
    expect(get(symptomKeysList)).toEqual([]);
  });
});

describe('refreshSymptomCatalogue', () => {
  it('transitions idle → ready on success', async () => {
    vi.mocked(listStandardSymptomKeys).mockResolvedValueOnce({
      keys: [{ symptom_key: 'headache' }, { symptom_key: 'cold' }],
    });

    const keys = await refreshSymptomCatalogue();

    expect(keys).toEqual(['headache', 'cold']);
    const state = get(symptomCatalogue);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect(state.keys).toEqual(['headache', 'cold']);
    }
  });

  it('falls back to the local constant on error and re-throws', async () => {
    vi.mocked(listStandardSymptomKeys).mockRejectedValueOnce(new Error('boom'));

    await expect(refreshSymptomCatalogue()).rejects.toThrow('boom');

    const state = get(symptomCatalogue);
    expect(state.status).toBe('ready');
    if (state.status === 'ready') {
      expect([...state.keys].sort()).toEqual([
        'back_pain',
        'cold',
        'digestion',
        'fatigue',
        'headache',
      ]);
    }
  });
});

describe('resetSymptomsStore', () => {
  it('clears the cache back to idle', async () => {
    vi.mocked(listStandardSymptomKeys).mockResolvedValueOnce({
      keys: [{ symptom_key: 'fatigue' }],
    });
    await refreshSymptomCatalogue();
    expect(get(symptomCatalogue).status).toBe('ready');

    resetSymptomsStore();
    expect(get(symptomCatalogue).status).toBe('idle');
  });
});
