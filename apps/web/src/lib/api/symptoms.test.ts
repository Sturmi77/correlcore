/**
 * Tests for the symptoms API client (Issue #9 + Issue #57 Custom-Symptome).
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
  assignSymptomsToEntry,
  createSymptom,
  deleteSymptom,
  listDefaultSymptoms,
  listSymptomsForEntry,
  listVisibleSymptoms,
  updateSymptom,
} from './symptoms';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('constants', () => {
  it('uses the documented intensity bounds', () => {
    expect(INTENSITY_MIN).toBe(0);
    expect(INTENSITY_MAX).toBe(3);
  });

  it('caps the per-entry symptom count at 32', () => {
    expect(MAX_SYMPTOMS_PER_ENTRY).toBe(32);
  });
});

describe('listDefaultSymptoms', () => {
  it('GETs /symptoms/default', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listDefaultSymptoms();
    expect(api.get).toHaveBeenCalledWith('/symptoms/default');
  });
});

describe('listVisibleSymptoms', () => {
  it('GETs /symptoms', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([]);
    await listVisibleSymptoms();
    expect(api.get).toHaveBeenCalledWith('/symptoms');
  });
});

describe('createSymptom', () => {
  it('POSTs to /symptoms with the payload', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ id: 's1' });
    await createSymptom({
      slug: 'migraene_aura',
      name: 'Migräne mit Aura',
      icon: '🧠',
    });
    expect(api.post).toHaveBeenCalledWith('/symptoms', {
      slug: 'migraene_aura',
      name: 'Migräne mit Aura',
      icon: '🧠',
    });
  });
});

describe('updateSymptom', () => {
  it('PATCHes /symptoms/{id}', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ id: 's1' });
    await updateSymptom('s1', { name: 'Renamed' });
    expect(api.patch).toHaveBeenCalledWith('/symptoms/s1', { name: 'Renamed' });
  });
});

describe('deleteSymptom', () => {
  it('DELETEs /symptoms/{id}', async () => {
    vi.mocked(api.delete).mockResolvedValueOnce(undefined);
    await deleteSymptom('s1');
    expect(api.delete).toHaveBeenCalledWith('/symptoms/s1');
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
      { symptom_id: 's-headache', intensity: 2 },
      { symptom_id: 's-cold', intensity: 1 },
    ]);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/symptoms', {
      symptoms: [
        { symptom_id: 's-headache', intensity: 2 },
        { symptom_id: 's-cold', intensity: 1 },
      ],
    });
  });

  it('sends an empty list to clear all symptoms', async () => {
    vi.mocked(api.put).mockResolvedValueOnce([]);
    await assignSymptomsToEntry('e1', []);
    expect(api.put).toHaveBeenCalledWith('/entries/e1/symptoms', { symptoms: [] });
  });
});
