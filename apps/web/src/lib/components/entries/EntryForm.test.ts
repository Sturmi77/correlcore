import { fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { readable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EntryDeltaResponse, EntryResponse } from '$lib/api/entries';
import { fetchEntryDelta, listEntries, updateEntry } from '$lib/api/entries';
import { submitEntry } from '$lib/stores/entries';
import EntryForm from './EntryForm.svelte';

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

const testHelpers = vi.hoisted(() => {
  function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
      resolve = res;
    });
    return { promise, resolve };
  }

  function mockComponent(testId: string) {
    return function MockComponent(anchor: Element | Comment) {
      const el = document.createElement('div');
      el.setAttribute('data-testid', testId);
      anchor.parentNode?.insertBefore(el, anchor);

      return {
        $on() {
          return () => {};
        },
        $set() {},
        $destroy() {
          el.remove();
        },
      };
    };
  }

  return { deferred, mockComponent };
});

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

vi.mock('$lib/api/entries', () => ({
  fetchEntryDelta: vi.fn(),
  listEntries: vi.fn(),
  updateEntry: vi.fn(),
}));

vi.mock('$lib/stores/entries', () => ({
  submitEntry: vi.fn(async (payload) => ({
    id: 'created-entry',
    user_id: 'user-1',
    source: 'manual',
    created_at: '2026-06-02T12:00:00Z',
    updated_at: '2026-06-02T12:00:00Z',
    note: payload.note ?? null,
    cycle_day: payload.cycle_day ?? null,
    slot: payload.slot ?? 'day',
    ...payload,
  })),
}));

vi.mock('$lib/api/tags', () => ({
  assignTagsToEntry: vi.fn(async () => {}),
  listTagsForEntry: vi.fn(async () => []),
}));

vi.mock('$lib/api/onboarding', () => ({
  completeOnboarding: vi.fn(),
  fetchTagSuggestions: vi.fn(async () => ({ groups: [] })),
}));

vi.mock('$lib/api/symptoms', () => ({
  assignSymptomsToEntry: vi.fn(async () => {}),
  listSymptomsForEntry: vi.fn(async () => []),
}));

vi.mock('$lib/stores/tags', () => ({
  refreshTags: vi.fn(async () => {}),
}));

vi.mock('$lib/offline/featureFlag', () => ({
  canUseOfflineSync: vi.fn(() => false),
}));

vi.mock('$lib/offline/syncOrchestrator', () => ({
  onLocalEntrySaved: vi.fn(),
  scheduleSync: vi.fn(),
  syncOrchestrator: readable({ badge: null, conflictNote: null }),
}));

vi.mock('$lib/stores/entriesOffline', () => ({
  findLocalEntryByDateSlot: vi.fn(),
  localEntryToFormFields: vi.fn(),
  saveEntryOffline: vi.fn(),
}));

vi.mock('$lib/components/entries/TagPicker.svelte', () => ({
  default: testHelpers.mockComponent('tag-picker-mock'),
}));

vi.mock('$lib/components/entries/SymptomChecker.svelte', () => ({
  default: testHelpers.mockComponent('symptom-checker-mock'),
}));

vi.mock('$lib/components/entries/DayDeltaCard.svelte', () => ({
  default: testHelpers.mockComponent('day-delta-card-mock'),
}));

vi.mock('$lib/components/entries/OnboardingTagSuggestions.svelte', () => ({
  default: testHelpers.mockComponent('onboarding-tags-mock'),
}));

vi.mock('$lib/components/common/ThemeToggle.svelte', () => ({
  default: testHelpers.mockComponent('theme-toggle-mock'),
}));

async function flushAsync(): Promise<void> {
  await Promise.resolve();
  await tick();
  await Promise.resolve();
  await tick();
}

function deltaWithPrevious(
  overrides: Partial<EntryDeltaResponse['previous']> = {}
): EntryDeltaResponse {
  return {
    today: null,
    previous: {
      entry_date: '2026-06-01',
      slot: 'day',
      mood_score: 4,
      energy: 2,
      stress: 5,
      ...overrides,
    },
    delta: { mood: null, energy: null, stress: null },
    shared_tags: [],
  };
}

describe('EntryForm smart defaults', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(listEntries).mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('applies previous-entry defaults without creating an entry until the user edits', async () => {
    const delta = testHelpers.deferred<EntryDeltaResponse>();
    vi.mocked(fetchEntryDelta).mockReturnValue(delta.promise);

    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();
    expect(listEntries).toHaveBeenCalledWith({
      start_date: '2026-06-02',
      end_date: '2026-06-02',
      limit: 5,
    });

    delta.resolve(deltaWithPrevious());
    await flushAsync();

    expect(screen.getByLabelText('entry.mood_label').getAttribute('aria-valuenow')).toBe('4');
    expect(screen.getByLabelText('entry.energy_label').getAttribute('aria-valuenow')).toBe('2');
    expect(screen.getByLabelText('entry.stress_label').getAttribute('aria-valuenow')).toBe('5');

    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();
    expect(submitEntry).not.toHaveBeenCalled();
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('idle');

    await fireEvent.click(screen.getByLabelText('entry.mood_increment'));
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(submitEntry).toHaveBeenCalledTimes(1);
    expect(submitEntry).toHaveBeenCalledWith(
      expect.objectContaining({
        entry_date: '2026-06-02',
        slot: 'day',
        mood_score: 5,
        energy: 2,
        stress: 5,
      })
    );
  });
});

describe('EntryForm slot changes', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(listEntries).mockResolvedValue([]);
    vi.mocked(fetchEntryDelta).mockResolvedValue({
      today: null,
      previous: null,
      delta: { mood: null, energy: null, stress: null },
      shared_tags: [],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('keeps dirty draft edits when selecting a time slot', async () => {
    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'draft before slot switch' },
    });
    await flushAsync();

    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('dirty');

    await fireEvent.click(screen.getByRole('button', { name: 'entry.time_slot.morning' }));
    await flushAsync();

    expect(
      screen.getByRole('button', { name: 'entry.time_slot.morning' }).getAttribute('aria-pressed')
    ).toBe('true');
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('dirty');

    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(submitEntry).toHaveBeenCalledTimes(1);
    expect(submitEntry).toHaveBeenCalledWith(
      expect.objectContaining({
        entry_date: '2026-06-02',
        slot: 'morning',
        note: 'draft before slot switch',
      })
    );
  });

  it('persists a selected slot after an in-flight draft create completes', async () => {
    const create = testHelpers.deferred<EntryResponse>();
    vi.mocked(submitEntry).mockReturnValue(create.promise);
    vi.mocked(updateEntry).mockResolvedValue({
      id: 'created-entry',
      user_id: 'user-1',
      entry_date: '2026-06-02',
      slot: 'morning',
      mood_score: 4,
      energy: 3,
      stress: 3,
      cycle_day: null,
      source: 'direct',
      work_context: 'homeoffice',
      note: null,
      created_at: '2026-06-02T12:00:00Z',
      updated_at: '2026-06-02T12:01:00Z',
    });

    render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();
    await fireEvent.click(screen.getByLabelText('entry.mood_increment'));
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(submitEntry).toHaveBeenCalledWith(
      expect.objectContaining({ slot: 'day', mood_score: 4 })
    );

    await fireEvent.click(screen.getByRole('button', { name: 'entry.time_slot.morning' }));
    await flushAsync();
    expect(
      screen.getByRole('button', { name: 'entry.time_slot.morning' }).getAttribute('aria-pressed')
    ).toBe('true');

    create.resolve({
      id: 'created-entry',
      user_id: 'user-1',
      entry_date: '2026-06-02',
      slot: 'day',
      mood_score: 4,
      energy: 3,
      stress: 3,
      cycle_day: null,
      source: 'direct',
      work_context: 'homeoffice',
      note: null,
      created_at: '2026-06-02T12:00:00Z',
      updated_at: '2026-06-02T12:00:00Z',
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).toHaveBeenCalledWith(
      'created-entry',
      expect.objectContaining({ slot: 'morning', mood_score: 4 })
    );
  });

  it('hydrates an occupied slot instead of posting a duplicate draft', async () => {
    vi.mocked(listEntries).mockResolvedValue([
      {
        id: 'morning-entry',
        user_id: 'user-1',
        entry_date: '2026-06-02',
        slot: 'morning',
        mood_score: 2,
        energy: 3,
        stress: 4,
        cycle_day: null,
        source: 'direct',
        work_context: 'homeoffice',
        note: 'existing morning note',
        created_at: '2026-06-02T08:00:00Z',
        updated_at: '2026-06-02T08:00:00Z',
      },
    ]);

    render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'draft on blank day slot' },
    });
    await flushAsync();

    await fireEvent.click(screen.getByRole('button', { name: 'entry.time_slot.morning' }));
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(submitEntry).not.toHaveBeenCalledWith(expect.objectContaining({ slot: 'morning' }));
    expect(
      (screen.getByPlaceholderText('entry.note_placeholder') as HTMLTextAreaElement).value
    ).toBe('existing morning note');
  });

  it('uses the last slot click after autosave settles on an existing entry', async () => {
    vi.mocked(listEntries).mockImplementation(async ({ start_date, end_date }) => {
      if (start_date !== '2026-06-02' || end_date !== '2026-06-02') return [];
      return [
        {
          id: 'day-entry',
          user_id: 'user-1',
          entry_date: '2026-06-02',
          slot: 'day',
          mood_score: 3,
          energy: 3,
          stress: 3,
          cycle_day: null,
          source: 'direct',
          work_context: 'homeoffice',
          note: 'day note',
          created_at: '2026-06-02T12:00:00Z',
          updated_at: '2026-06-02T12:00:00Z',
        },
        {
          id: 'evening-entry',
          user_id: 'user-1',
          entry_date: '2026-06-02',
          slot: 'evening',
          mood_score: 1,
          energy: 2,
          stress: 5,
          cycle_day: null,
          source: 'direct',
          work_context: 'homeoffice',
          note: 'evening note',
          created_at: '2026-06-02T20:00:00Z',
          updated_at: '2026-06-02T20:00:00Z',
        },
      ];
    });

    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited day note' },
    });
    await flushAsync();

    const morningButton = screen.getByRole('button', { name: 'entry.time_slot.morning' });
    const eveningButton = screen.getByRole('button', { name: 'entry.time_slot.evening' });

    void fireEvent.click(morningButton);
    await flushAsync();
    await fireEvent.click(eveningButton);
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).toHaveBeenCalledWith(
      'day-entry',
      expect.objectContaining({ note: 'edited day note' })
    );
    expect(
      (screen.getByPlaceholderText('entry.note_placeholder') as HTMLTextAreaElement).value
    ).toBe('evening note');
    expect(eveningButton.getAttribute('aria-pressed')).toBe('true');
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('idle');
  });
});
