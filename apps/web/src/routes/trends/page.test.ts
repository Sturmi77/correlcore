import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { setAnalysisRange } from '$lib/stores/analysisRange';
import { fetchSymptomHeatmap, fetchTimeseries } from '$lib/api/stats';
import { listEntries } from '$lib/api/entries';
import { ApiError } from '$lib/api/client';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com' },
    }),
  };
});

vi.mock('$lib/api/stats', () => ({
  fetchTimeseries: vi.fn(async (range: string) => ({
    range,
    points: [
      {
        period_start: '2026-05-15',
        period_end: '2026-05-15',
        entry_count: 1,
        mood_avg: 3,
        energy_avg: 4,
        stress_avg: 4,
      },
      {
        period_start: '2026-05-16',
        period_end: '2026-05-16',
        entry_count: 1,
        mood_avg: 4,
        energy_avg: 3,
        stress_avg: 2,
      },
    ],
  })),
  fetchTagHeatmap: vi.fn(async () => ({
    start_date: '2026-05-01',
    end_date: '2026-05-16',
    tags: [
      {
        tag_id: 'focus',
        slug: 'focus',
        name: 'Focus',
        category: 'work',
        color: null,
        days: [{ date: '2026-05-16', count: 2 }],
      },
    ],
  })),
  fetchSymptomHeatmap: vi.fn(async () => ({
    start_date: '2026-05-01',
    end_date: '2026-05-16',
    symptoms: [
      {
        symptom_id: 'fatigue',
        slug: 'fatigue',
        name: 'Fatigue',
        icon: null,
        days: [{ date: '2026-05-16', count: 1, max_intensity: 2 }],
      },
    ],
  })),
  fetchEntryStreak: vi.fn(async () => ({
    current_streak: 2,
    longest_streak: 5,
    total_entry_days: 12,
    last_entry_date: '2026-05-16',
    as_of: '2026-05-16',
  })),
}));

vi.mock('$lib/api/habits', () => ({
  listHabits: vi.fn(async () => ({ habits: [] })),
}));

vi.mock('$lib/api/entries', () => ({
  listEntries: vi.fn(async () => [
    {
      id: 'entry-office',
      user_id: 'user-1',
      entry_date: '2026-05-16',
      slot: 'day',
      mood_score: 4,
      energy: 3,
      stress: 2,
      cycle_day: null,
      source: 'direct',
      work_context: 'office',
      note: null,
      created_at: '2026-05-16T08:00:00Z',
      updated_at: '2026-05-16T08:00:00Z',
    },
  ]),
}));

vi.mock('$lib/api/tags', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/tags')>('$lib/api/tags');
  return {
    ...actual,
    listTagsForEntry: vi.fn(async () => []),
    listVisibleTags: vi.fn(async () => []),
  };
});

vi.mock('$lib/api/symptoms', () => ({
  listVisibleSymptoms: vi.fn(async () => []),
  listSymptomsForEntry: vi.fn(async () => []),
}));

describe('/trends page', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('renders compare and habits tabs with health context on compare', async () => {
    render(Page);

    expect(await screen.findByTestId('trends-sticky-toolbar')).toBeTruthy();
    // Compare hides range chips (fixed 365d zoom axis).
    expect(screen.queryByTestId('trends-range-control')).toBeNull();
    expect(await screen.findByTestId('trends-tab-compare')).toBeTruthy();
    expect(screen.queryByTestId('trends-tab-health')).toBeNull();
    expect(screen.getByTestId('trends-tab-habits')).toBeTruthy();
    expect(screen.getByTestId('trends-health-context')).toBeTruthy();
    expect(screen.getByText('trends.health.heading')).toBeTruthy();
  });

  it('switches to Habits tab', async () => {
    render(Page);

    const habits = await screen.findByTestId('trends-tab-habits');
    await fireEvent.click(habits);

    await waitFor(() => {
      expect(habits.getAttribute('aria-selected')).toBe('true');
    });
    expect(screen.getByTestId('habits-panel')).toBeTruthy();
  });

  it('keeps the desktop comparison canvas visible', async () => {
    render(Page);
    expect(await screen.findByTestId('mobile-trends-detail')).toBeTruthy();
    expect(screen.queryByTestId('mobile-trends-summary')).toBeNull();
  });

  it('renders work context as a compare context row', async () => {
    render(Page);

    expect(await screen.findByText('entry.work_context.office')).toBeTruthy();
    expect(screen.getByText('trends.compare.work_contexts')).toBeTruthy();
  });

  it('uses scroll-first composition on mobile with summary, sticky quick filters, and detail canvas', async () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn(() => ({
        matches: true,
        media: '(max-width: 767px)',
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    render(Page);
    expect(await screen.findByTestId('mobile-trends-summary')).toBeTruthy();
    expect(screen.getByTestId('mobile-trends-detail')).toBeTruthy();
    // #786: quick filters live in the sticky ScreenHeader controls slot.
    expect(screen.getByTestId('trends-compare-quick-filters')).toBeTruthy();
    expect(screen.getByTestId('trends-filters-toolbar')).toBeTruthy();
    expect(screen.queryByTestId('mobile-trends-detail-toggle')).toBeNull();
  });

  it('loads Compare with a fixed year window and hides range chips', async () => {
    localStorage.clear();
    setAnalysisRange('week');
    vi.mocked(fetchTimeseries).mockClear();

    render(Page);
    expect(await screen.findByTestId('trends-compare-panel')).toBeTruthy();
    expect(screen.queryByTestId('trends-range-control')).toBeNull();

    await waitFor(() => {
      expect(vi.mocked(fetchTimeseries).mock.calls.at(-1)?.[0]).toBe('year');
    });
  });

  it('loads the newly selected range on Habits when the control changes', async () => {
    localStorage.clear();
    setAnalysisRange('week');
    vi.mocked(fetchTimeseries).mockClear();
    vi.mocked(listEntries).mockClear();

    render(Page);
    await fireEvent.click(await screen.findByTestId('trends-tab-habits'));
    await screen.findByTestId('trends-range-control');

    await fireEvent.click(screen.getByTestId('trends-range-year'));

    await waitFor(() => {
      expect(vi.mocked(fetchTimeseries).mock.calls.at(-1)?.[0]).toBe('year');
    });

    const callsAfterRangeChange = vi
      .mocked(fetchTimeseries)
      .mock.calls.filter((call) => call[0] === 'year');
    expect(callsAfterRangeChange.length).toBeGreaterThan(0);
  });

  it('keeps Compare usable when symptom heatmap returns 401', async () => {
    vi.mocked(fetchSymptomHeatmap).mockRejectedValueOnce(
      new ApiError(401, 'Could not validate credentials', '/entries/stats/symptoms')
    );

    render(Page);

    expect(await screen.findByTestId('trends-sticky-toolbar')).toBeTruthy();
    expect(await screen.findByText('entry.work_context.office')).toBeTruthy();
    expect(screen.queryByText(/API 401 on \/entries\/stats\/symptoms/)).toBeNull();
  });
});
