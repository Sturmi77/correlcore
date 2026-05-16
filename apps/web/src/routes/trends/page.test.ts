import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
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
  fetchTimeseries: vi.fn(async (range: string) => ({ range, points: [] })),
  fetchTagHeatmap: vi.fn(async () => ({
    start_date: '2026-05-01',
    end_date: '2026-05-16',
    tags: [],
  })),
  fetchEntryStreak: vi.fn(async () => ({
    current_streak: 2,
    longest_streak: 5,
    total_entry_days: 12,
    last_entry_date: '2026-05-16',
    as_of: '2026-05-16',
  })),
}));

vi.mock('$lib/api/entries', () => ({
  listEntries: vi.fn(async () => []),
}));

vi.mock('$lib/api/tags', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/tags')>('$lib/api/tags');
  return {
    ...actual,
    listTagsForEntry: vi.fn(async () => []),
  };
});

vi.mock('$lib/api/symptoms', () => ({
  listVisibleSymptoms: vi.fn(async () => []),
  listSymptomsForEntry: vi.fn(async () => []),
}));

describe('/trends page', () => {
  it('renders canonical tabs and switches to Health', async () => {
    render(Page);

    expect(await screen.findByTestId('trends-tab-mood')).toBeTruthy();
    expect(screen.getByTestId('trends-tab-activities')).toBeTruthy();
    const health = screen.getByTestId('trends-tab-health');

    await fireEvent.click(health);
    await waitFor(() => {
      expect(health.getAttribute('aria-selected')).toBe('true');
    });
    expect(screen.getByText('trends.health.heading')).toBeTruthy();
  });
});
