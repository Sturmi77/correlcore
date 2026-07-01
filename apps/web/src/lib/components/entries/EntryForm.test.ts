import { fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { readable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EntryDeltaResponse } from '$lib/api/entries';
import { fetchEntryDelta, listEntries } from '$lib/api/entries';
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
