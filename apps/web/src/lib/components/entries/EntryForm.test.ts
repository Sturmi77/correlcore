import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import { readable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EntryDeltaResponse, EntryResponse } from '$lib/api/entries';
import { fetchEntryDelta, listEntries, updateEntry } from '$lib/api/entries';
import { completeOnboarding } from '$lib/api/onboarding';
import type { EntrySymptomResponse } from '$lib/api/symptoms';
import { assignSymptomsToEntry, listSymptomsForEntry } from '$lib/api/symptoms';
import type { TagResponse } from '$lib/api/tags';
import { assignTagsToEntry, listTagsForEntry } from '$lib/api/tags';
import { canUseOfflineSync } from '$lib/offline/featureFlag';
import { hydrateServerEntryFromApi, saveEntryOffline } from '$lib/stores/entriesOffline';
import { connectivity } from '$lib/stores/connectivity';
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
  findLocalEntryByDateSlot: vi.fn(async () => undefined),
  hydrateServerEntryFromApi: vi.fn(async () => undefined),
  localEntryToFormFields: vi.fn(),
  saveEntryOffline: vi.fn(),
  shouldPreferLocalEntry: vi.fn(() => false),
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

  it('flushes dirty edits against the previous date before hydrating a new date', async () => {
    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-05' },
    });

    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'draft before date change' },
    });
    await flushAsync();

    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('dirty');

    await fireEvent.input(screen.getByLabelText('entry.date_label'), {
      target: { value: '2026-06-06' },
    });
    await flushAsync();

    expect(submitEntry).toHaveBeenCalledTimes(1);
    expect(submitEntry).toHaveBeenCalledWith(
      expect.objectContaining({
        entry_date: '2026-06-05',
        slot: 'day',
        work_context: 'homeoffice',
        note: 'draft before date change',
      })
    );
    await waitFor(() => {
      expect(listEntries).toHaveBeenCalledWith({
        start_date: '2026-06-06',
        end_date: '2026-06-06',
        limit: 5,
      });
    });
    await waitFor(() => {
      expect(
        (screen.getByPlaceholderText('entry.note_placeholder') as HTMLTextAreaElement).value
      ).toBe('');
    });
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

  it('ignores slot clicks while a date-change save is still settling', async () => {
    const create = testHelpers.deferred<EntryResponse>();
    vi.mocked(submitEntry).mockReturnValue(create.promise);

    render(EntryForm, {
      props: { initialDate: '2026-06-05' },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'friday draft' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(submitEntry).toHaveBeenCalledWith(
      expect.objectContaining({ entry_date: '2026-06-05', slot: 'day', note: 'friday draft' })
    );

    await fireEvent.input(screen.getByLabelText('entry.date_label'), {
      target: { value: '2026-06-06' },
    });
    await flushAsync();

    const morningButton = screen.getByRole('button', { name: 'entry.time_slot.morning' });
    expect(morningButton.hasAttribute('disabled')).toBe(true);

    await fireEvent.click(morningButton);
    await flushAsync();

    expect(morningButton.getAttribute('aria-pressed')).toBe('false');

    create.resolve({
      id: 'created-entry',
      user_id: 'user-1',
      entry_date: '2026-06-05',
      slot: 'day',
      mood_score: 3,
      energy: 3,
      stress: 3,
      cycle_day: null,
      source: 'direct',
      work_context: 'homeoffice',
      note: 'friday draft',
      created_at: '2026-06-05T12:00:00Z',
      updated_at: '2026-06-05T12:00:00Z',
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(listEntries).toHaveBeenCalledWith({
        start_date: '2026-06-06',
        end_date: '2026-06-06',
        limit: 5,
      });
    });
  });

  it('does not move an existing entry when an empty slot is clicked during an in-flight save', async () => {
    const patch = testHelpers.deferred<EntryResponse>();
    vi.mocked(listEntries).mockResolvedValue([
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
    ]);
    vi.mocked(updateEntry).mockReturnValueOnce(patch.promise).mockResolvedValue({
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
      note: 'edited day note',
      created_at: '2026-06-02T12:00:00Z',
      updated_at: '2026-06-02T12:01:00Z',
    });

    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-02' },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited day note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).toHaveBeenCalledWith(
      'day-entry',
      expect.objectContaining({ slot: 'day', note: 'edited day note' })
    );
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('saving');

    await fireEvent.click(screen.getByRole('button', { name: 'entry.time_slot.morning' }));
    await flushAsync();

    patch.resolve({
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
      note: 'edited day note',
      created_at: '2026-06-02T12:00:00Z',
      updated_at: '2026-06-02T12:01:00Z',
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).toHaveBeenCalledTimes(1);
    expect(
      (screen.getByPlaceholderText('entry.note_placeholder') as HTMLTextAreaElement).value
    ).toBe('');
    expect(
      screen.getByRole('button', { name: 'entry.time_slot.morning' }).getAttribute('aria-pressed')
    ).toBe('true');
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('idle');
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
    vi.mocked(listEntries).mockImplementation(async (query = {}) => {
      const { start_date, end_date } = query;
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

describe('EntryForm offline sync edge cases (R-04 / R-05)', () => {
  const onlineDescriptor = Object.getOwnPropertyDescriptor(navigator, 'onLine');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(canUseOfflineSync).mockReturnValue(true);
    vi.mocked(listEntries).mockResolvedValue([]);
    vi.mocked(fetchEntryDelta).mockResolvedValue({
      today: null,
      previous: null,
      delta: { mood: null, energy: null, stress: null },
      shared_tags: [],
    });
    vi.mocked(saveEntryOffline).mockResolvedValue({ entryId: 'local-entry', syncState: 'pending' });
    vi.mocked(completeOnboarding).mockResolvedValue({
      created_tags: [],
      onboarding_retro_completed: true,
      onboarding_profile_completed: true,
    });
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      get: () => true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.mocked(canUseOfflineSync).mockReturnValue(false);
    if (onlineDescriptor) {
      Object.defineProperty(navigator, 'onLine', onlineDescriptor);
    } else {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        get: () => true,
      });
    }
  });

  it('does not hydrate IndexedDB with stale tags when the tags fetch fails (R-05)', async () => {
    const serverEntry: EntryResponse = {
      id: 'server-entry-b',
      user_id: 'user-1',
      entry_date: '2026-06-03',
      slot: 'day',
      mood_score: 2,
      energy: 2,
      stress: 2,
      cycle_day: null,
      source: 'direct',
      work_context: 'homeoffice',
      note: 'entry B',
      created_at: '2026-06-03T12:00:00Z',
      updated_at: '2026-06-03T12:00:00Z',
    };
    vi.mocked(listEntries).mockResolvedValue([serverEntry]);
    vi.mocked(listTagsForEntry).mockRejectedValue(new Error('tags unavailable'));
    vi.mocked(listSymptomsForEntry).mockResolvedValue([]);

    render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();

    expect(listEntries).toHaveBeenCalled();
    expect(listTagsForEntry).toHaveBeenCalledWith('server-entry-b');
    expect(hydrateServerEntryFromApi).not.toHaveBeenCalled();
  });

  it('finalizes onboarding while online even when offline sync is enabled (R-04)', async () => {
    render(EntryForm, {
      props: { initialDate: '2026-06-02', onboardingTagsEnabled: true },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'first entry' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(completeOnboarding).toHaveBeenCalledTimes(1);
    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
  });

  it('defers onboarding finalize when offline sync is on and the device is offline (R-04)', async () => {
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      get: () => false,
    });

    render(EntryForm, {
      props: { initialDate: '2026-06-02', onboardingTagsEnabled: true },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'offline first entry' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(completeOnboarding).not.toHaveBeenCalled();
    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
  });
});

function tagResponse(id: string): TagResponse {
  return {
    id,
    user_id: 'user-1',
    slug: id,
    name: id,
    category: 'other',
    icon: null,
    color: null,
    is_default: false,
    is_hidden: false,
    include_in_analytics: true,
    habit_type: 'none',
    target_frequency: null,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
  };
}

function symptomResponse(symptomId: string, intensity: number): EntrySymptomResponse {
  return {
    id: `es-${symptomId}`,
    entry_id: 'server-entry-a',
    user_id: 'user-1',
    symptom_id: symptomId,
    intensity,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
  };
}

const relationServerEntry: EntryResponse = {
  id: 'server-entry-a',
  user_id: 'user-1',
  entry_date: '2026-06-03',
  slot: 'day',
  mood_score: 3,
  energy: 3,
  stress: 3,
  cycle_day: null,
  source: 'direct',
  work_context: 'homeoffice',
  note: 'original note',
  created_at: '2026-06-03T12:00:00Z',
  updated_at: '2026-06-03T12:00:00Z',
};

// P1a — a failed per-entry tag/symptom fetch during load must never let the
// autosave persist an *empty* replace-set and silently delete the entry's
// existing relations. The save path re-resolves the affected relation first;
// if it still cannot load, the save is blocked (retryable) rather than
// destructive.
describe('EntryForm relation preservation after failed load fetch (P1a, online)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(canUseOfflineSync).mockReturnValue(false);
    vi.mocked(listEntries).mockResolvedValue([relationServerEntry]);
    vi.mocked(fetchEntryDelta).mockResolvedValue({
      today: null,
      previous: null,
      delta: { mood: null, energy: null, stress: null },
      shared_tags: [],
    });
    vi.mocked(listSymptomsForEntry).mockResolvedValue([]);
    vi.mocked(updateEntry).mockResolvedValue({
      ...relationServerEntry,
      note: 'edited note',
      updated_at: '2026-06-03T12:05:00Z',
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('re-resolves and preserves the entry tags before the replace-set save', async () => {
    vi.mocked(listTagsForEntry)
      .mockRejectedValueOnce(new Error('tags unavailable'))
      .mockResolvedValue([tagResponse('tag-x'), tagResponse('tag-y')]);

    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();
    expect(listTagsForEntry).toHaveBeenCalledWith('server-entry-a');

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(updateEntry).toHaveBeenCalledWith(
      'server-entry-a',
      expect.objectContaining({ note: 'edited note' })
    );
    // Preserved: the replace-set carries the re-resolved tags…
    expect(assignTagsToEntry).toHaveBeenCalledWith('server-entry-a', ['tag-x', 'tag-y']);
    // …and never the destructive empty set.
    expect(assignTagsToEntry).not.toHaveBeenCalledWith('server-entry-a', []);
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).not.toBe('error');
  });

  it('re-resolves and preserves the entry symptoms before the replace-set save', async () => {
    vi.mocked(listTagsForEntry).mockResolvedValue([]);
    vi.mocked(listSymptomsForEntry)
      .mockRejectedValueOnce(new Error('symptoms unavailable'))
      .mockResolvedValue([symptomResponse('sym-a', 2)]);

    render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(assignSymptomsToEntry).toHaveBeenCalledWith('server-entry-a', [
      { symptom_id: 'sym-a', intensity: 2 },
    ]);
    expect(assignSymptomsToEntry).not.toHaveBeenCalledWith('server-entry-a', []);
  });

  it('blocks the save instead of writing an empty replace-set when the fetch keeps failing', async () => {
    vi.mocked(listTagsForEntry).mockRejectedValue(new Error('tags unavailable'));

    const { container } = render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    // No destructive relation write, and the entry save is held back too
    // (a full snapshot cannot be persisted without the true relations).
    expect(assignTagsToEntry).not.toHaveBeenCalled();
    expect(updateEntry).not.toHaveBeenCalled();
    expect(container.querySelector('form')?.getAttribute('data-autosave-status')).toBe('error');
  });
});

describe('EntryForm relation preservation after failed load fetch (P1a, offline sync)', () => {
  const onlineDescriptor = Object.getOwnPropertyDescriptor(navigator, 'onLine');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(canUseOfflineSync).mockReturnValue(true);
    vi.mocked(listEntries).mockResolvedValue([relationServerEntry]);
    vi.mocked(fetchEntryDelta).mockResolvedValue({
      today: null,
      previous: null,
      delta: { mood: null, energy: null, stress: null },
      shared_tags: [],
    });
    vi.mocked(listSymptomsForEntry).mockResolvedValue([]);
    vi.mocked(saveEntryOffline).mockResolvedValue({
      entryId: 'server-entry-a',
      syncState: 'pending',
    });
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.mocked(canUseOfflineSync).mockReturnValue(false);
    if (onlineDescriptor) {
      Object.defineProperty(navigator, 'onLine', onlineDescriptor);
    } else {
      Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true });
    }
  });

  it('writes the re-resolved tag set — not an empty one — into the offline snapshot', async () => {
    vi.mocked(listTagsForEntry)
      .mockRejectedValueOnce(new Error('tags unavailable'))
      .mockResolvedValue([tagResponse('tag-x'), tagResponse('tag-y')]);

    render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
    const [, snap] = vi.mocked(saveEntryOffline).mock.calls[0];
    expect(snap.selectedTagIds).toEqual(['tag-x', 'tag-y']);
    expect(saveEntryOffline).not.toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ selectedTagIds: [] })
    );
  });

  it('blocks the offline save when the relation cannot be re-resolved', async () => {
    vi.mocked(listTagsForEntry).mockRejectedValue(new Error('tags unavailable'));

    render(EntryForm, {
      props: { initialDate: '2026-06-03' },
    });

    await flushAsync();
    await flushAsync();

    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'edited note' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(saveEntryOffline).not.toHaveBeenCalled();
  });
});

// P1b — onboarding must not finalize (a network call) when the API is
// unreachable, even if the browser reports itself online. Otherwise
// `completeOnboarding` throws and aborts the save before the entry is
// persisted locally, losing the first onboarding entry.
describe('EntryForm onboarding deferral on unreachable API (P1b)', () => {
  const onlineDescriptor = Object.getOwnPropertyDescriptor(navigator, 'onLine');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(canUseOfflineSync).mockReturnValue(true);
    vi.mocked(listEntries).mockResolvedValue([]);
    vi.mocked(fetchEntryDelta).mockResolvedValue({
      today: null,
      previous: null,
      delta: { mood: null, energy: null, stress: null },
      shared_tags: [],
    });
    vi.mocked(saveEntryOffline).mockResolvedValue({ entryId: 'local-entry', syncState: 'pending' });
    vi.mocked(completeOnboarding).mockResolvedValue({
      created_tags: [],
      onboarding_retro_completed: true,
      onboarding_profile_completed: true,
    });
    connectivity._resetForTests();
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.mocked(canUseOfflineSync).mockReturnValue(false);
    connectivity._resetForTests();
    if (onlineDescriptor) {
      Object.defineProperty(navigator, 'onLine', onlineDescriptor);
    } else {
      Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true });
    }
  });

  it('defers onboarding when the browser is online but the API is unreachable', async () => {
    connectivity.markServerReachable(false);

    render(EntryForm, {
      props: { initialDate: '2026-06-02', onboardingTagsEnabled: true },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'first entry' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    // The entry is persisted locally and the network finalize is deferred,
    // so the first onboarding entry is never lost.
    expect(completeOnboarding).not.toHaveBeenCalled();
    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
  });

  it('finalizes onboarding when the browser is online and the API is reachable (R-04)', async () => {
    connectivity.markServerReachable(true);

    render(EntryForm, {
      props: { initialDate: '2026-06-02', onboardingTagsEnabled: true },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'first entry' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(completeOnboarding).toHaveBeenCalledTimes(1);
    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
  });

  it('still saves the entry when finalize fails under a stale reachable flag (P1b)', async () => {
    // Connectivity still says reachable (last probe succeeded) but the
    // onboarding finalize call itself fails — without catch-and-defer the
    // throw aborts persist() before saveEntryOffline.
    connectivity.markServerReachable(true);
    vi.mocked(completeOnboarding).mockRejectedValue(new Error('API blip'));

    render(EntryForm, {
      props: { initialDate: '2026-06-02', onboardingTagsEnabled: true },
    });

    await flushAsync();
    await fireEvent.input(screen.getByPlaceholderText('entry.note_placeholder'), {
      target: { value: 'first entry despite finalize failure' },
    });
    await flushAsync();
    await vi.advanceTimersByTimeAsync(801);
    await flushAsync();

    expect(completeOnboarding).toHaveBeenCalledTimes(1);
    expect(saveEntryOffline).toHaveBeenCalledTimes(1);
  });
});
