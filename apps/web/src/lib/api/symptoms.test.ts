/**
 * Tests for the symptoms API client (Issue #9).
 *
 * The underlying `api` helper is mocked so the assertions are about
 * the call shape (path + body) the client emits — same pattern as
 * tags.test.ts.
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
  INTENSITY_MAX,
  INTENSITY_MIN,
  MAX_SYMPTOMS_PER_ENTRY,
  STANDARD_SYMPTOM_KEYS,
  assignSymptomsToEntry,
  listStandardSymptomKeys,
  listSymptomsForEntry,
} from './symptoms';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('STANDARD_SYMPTOM_KEYS', () => {
  it('exposes the canonical set of M1 standard keys', () => {
    expect([...STANDARD_SYMPTOM_KEYS].sort()).toEqual([
      'back_pain',
      'cold',
      'digestion',
      'fatigue',
      'headache',
    ]);
  });

  it('uses the documented intensity bounds', () => {
    expect(INTENSITY_MIN).toBe(0);
    expect(INTENSITY_MAX).toBe(3);
  });

  it('caps the per-entry symptom count at 32', () => {
    expect(MAX_SYMPTOMS_PER_ENTRY).toBe(32);
  });
});

describe('listStandardSymptomKeys', () => {
  it('GETs /symptoms/standard', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ keys: [] });
    await listStandardSymptomKeys();
    expect(api.get).toHaveBeenCalledWith('/symptoms/standard');
  });
});

describe('listSymptomsForEntry', () => {
  it('GETs /entries/{id}/symptoms', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listSymptomsForEntry('e1');
    expect(api.get).toHaveBeenCalledWith('/entries/e1/symptoms');
  });
});

describe('assignSymptomsToEntry', () => {
  it('PUTs the full symptom list to /entries/{id}/symptoms', async () => {
    vi.mocked(api.put).mockResolvedValueOnce([]);
    await assignSymptomsToEntry('e1', [
      { symptom_key: 'headache', intensity: 2 },
      { symptom_key: 'cold', intensity: 1 },
    ]);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/symptoms', {
      symptoms: [
        { symptom_key: 'headache', intensity: 2 },
        { symptom_key: 'cold', intensity: 1 },
      ],
    });
  });

  it('sends an empty list to clear all symptoms', async () => {
    vi.mocked(api.put).mockResolvedValueOnce([]);
    await assignSymptomsToEntry('e1', []);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/symptoms', { symptoms: [] });
  });
});
