import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_SYMPTOMS_PER_ENTRY, type SymptomEntry, type SymptomResponse } from '$lib/api/symptoms';
import SymptomChecker from './SymptomChecker.svelte';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (run: (formatter: (key: string) => string) => void) => {
      run((key: string) => key);
      return () => undefined;
    },
  },
}));

const symptomStoreMocks = vi.hoisted(() => ({
  state: undefined as unknown as {
    set(value: { status: 'ready'; symptoms: SymptomResponse[] }): void;
    subscribe(run: (value: { status: 'ready'; symptoms: SymptomResponse[] }) => void): () => void;
  },
  refreshSymptoms: vi.fn(),
  submitSymptom: vi.fn(),
}));

vi.mock('$lib/stores/symptoms', async () => {
  const { derived, writable } = await import('svelte/store');
  symptomStoreMocks.state = writable<{ status: 'ready'; symptoms: SymptomResponse[] }>({
    status: 'ready',
    symptoms: [],
  });
  return {
    symptoms: { subscribe: symptomStoreMocks.state.subscribe },
    symptomsList: derived(symptomStoreMocks.state, ($state) => $state.symptoms),
    refreshSymptoms: symptomStoreMocks.refreshSymptoms,
    submitSymptom: symptomStoreMocks.submitSymptom,
  };
});

const symptom: SymptomResponse = {
  id: 'symptom-headache',
  user_id: null,
  slug: 'headache',
  name: 'Headache',
  icon: null,
  is_default: true,
  created_at: '2026-05-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
};

describe('SymptomChecker', () => {
  beforeEach(() => {
    symptomStoreMocks.state.set({ status: 'ready', symptoms: [symptom] });
  });

  it('explains the selection limit and blocks another symptom row', () => {
    const selected: SymptomEntry[] = Array.from({ length: MAX_SYMPTOMS_PER_ENTRY }, (_, index) => ({
      symptom_id: `selected-${index}`,
      intensity: 1,
    }));
    render(SymptomChecker, { props: { selected } });

    expect(screen.getByTestId('symptom-limit-message').textContent).toContain(
      'symptom.limit_reached'
    );
    expect(
      screen
        .getAllByRole('button', { name: /symptom\.intensity/ })
        .every((button) => (button as HTMLButtonElement).disabled)
    ).toBe(true);
  });
});
