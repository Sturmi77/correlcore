import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Page from './+page.svelte';
import type { SymptomResponse } from '$lib/api/symptoms';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return { auth: readable({ status: 'authenticated', user: { id: 'user-1' } }) };
});

vi.mock('$lib/api/symptoms', () => ({
  listVisibleSymptoms: vi.fn(),
  updateSymptom: vi.fn(),
  deleteSymptom: vi.fn(),
}));

vi.mock('$lib/stores/symptoms', () => ({ refreshSymptoms: vi.fn(async () => []) }));

import * as symptomsApi from '$lib/api/symptoms';

function symptom(overrides: Partial<SymptomResponse>): SymptomResponse {
  return {
    id: 'symptom-1',
    user_id: 'user-1',
    slug: 'headache',
    name: 'Headache',
    icon: null,
    is_default: false,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

describe('/settings/symptoms', () => {
  beforeEach(() => vi.clearAllMocks());

  it('separates editable custom symptoms from read-only defaults', async () => {
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValue([
      symptom({ id: 'custom', name: 'Migraine' }),
      symptom({ id: 'default', user_id: null, name: 'Fatigue', is_default: true }),
    ]);

    render(Page);

    expect(await screen.findByDisplayValue('Migraine')).toBeTruthy();
    expect(screen.getByText(/Fatigue/)).toBeTruthy();
    expect(screen.getAllByTestId('custom-symptom-row')).toHaveLength(1);
  });

  it('updates a custom symptom through the shared API', async () => {
    const current = symptom({ id: 'custom', name: 'Migraine' });
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValue([current]);
    vi.mocked(symptomsApi.updateSymptom).mockResolvedValue({ ...current, name: 'Aura' });
    render(Page);

    const input = await screen.findByDisplayValue('Migraine');
    await fireEvent.input(input, { target: { value: 'Aura' } });
    await fireEvent.click(screen.getByText('settings.symptoms.save'));

    await waitFor(() => {
      expect(symptomsApi.updateSymptom).toHaveBeenCalledWith('custom', {
        name: 'Aura',
        icon: null,
      });
    });
  });

  it('requires an explicit second action before deleting health data', async () => {
    vi.mocked(symptomsApi.listVisibleSymptoms).mockResolvedValue([
      symptom({ id: 'custom', name: 'Migraine' }),
    ]);
    vi.mocked(symptomsApi.deleteSymptom).mockResolvedValue(undefined);
    render(Page);

    await screen.findByDisplayValue('Migraine');
    await fireEvent.click(screen.getByText('settings.symptoms.delete'));
    expect(symptomsApi.deleteSymptom).not.toHaveBeenCalled();
    await fireEvent.click(screen.getByText('settings.symptoms.confirm_delete'));

    await waitFor(() => expect(symptomsApi.deleteSymptom).toHaveBeenCalledWith('custom'));
  });
});
