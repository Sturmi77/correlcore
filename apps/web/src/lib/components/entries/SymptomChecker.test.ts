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
    // The unselected symptom's presence toggle is disabled at the cap.
    expect((screen.getByTestId('symptom-toggle') as HTMLButtonElement).disabled).toBe(true);
  });

  it('records symptoms presence-only and hides the intensity levels (#544)', async () => {
    render(SymptomChecker, { props: { selected: [] as SymptomEntry[] } });
    // Intensity note is shown; no 0–3 intensity level buttons remain.
    expect(screen.getByTestId('symptom-intensity-note')).toBeTruthy();
    expect(screen.queryAllByRole('button', { name: /symptom\.intensity\.\d/ })).toHaveLength(0);

    // A single presence toggle drives selection.
    const toggle = screen.getByTestId('symptom-toggle') as HTMLButtonElement;
    expect(toggle.getAttribute('aria-pressed')).toBe('false');
    toggle.click();
    await Promise.resolve();
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
  });

  it('treats legacy intensity 0 as absent and upgrades on toggle', async () => {
    // Backend contract: intensity 0 = absent (analytics use intensity > 0).
    // The presence toggle must show "Not present" and the first click must
    // mark present — not clear the row.
    const selected: SymptomEntry[] = [{ symptom_id: symptom.id, intensity: 0 }];
    render(SymptomChecker, { props: { selected } });

    const toggle = screen.getByTestId('symptom-toggle') as HTMLButtonElement;
    expect(toggle.getAttribute('aria-pressed')).toBe('false');
    expect(toggle.textContent).toContain('symptom.present_off');
    expect(toggle.disabled).toBe(false);

    toggle.click();
    await Promise.resolve();

    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    expect(toggle.textContent).toContain('symptom.present_on');
  });
});
