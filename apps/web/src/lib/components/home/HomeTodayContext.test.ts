import { render, screen, fireEvent } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import HomeTodayContext from './HomeTodayContext.svelte';
import type { EntryResponse } from '$lib/api/entries';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
  locale: readable('en'),
}));

const entry: EntryResponse = {
  id: 'e1',
  user_id: 'u1',
  entry_date: '2026-05-15',
  slot: 'day',
  mood_score: 4,
  energy: 3,
  stress: 2,
  cycle_day: null,
  work_context: 'homeoffice',
  source: 'direct',
  note: null,
  created_at: '2026-05-15T10:00:00Z',
  updated_at: '2026-05-15T10:00:00Z',
};

describe('HomeTodayContext', () => {
  it('shows no-entry status when today has no entry', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: null, loading: false },
    });
    expect(screen.getByTestId('home-today-status').textContent).toContain('home.no_entry_today');
    expect(screen.queryByTestId('home-work-context')).toBeNull();
    expect(screen.getByTestId('home-today-action').textContent).toContain('home.cta_log_today');
  });

  it('shows work context and tracked status when entry exists', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: entry, loading: false },
    });
    expect(screen.getByTestId('home-work-context').textContent).toContain(
      'entry.work_context.homeoffice'
    );
    expect(screen.getByTestId('home-today-status').textContent).toContain(
      'home.entry_today_present'
    );
    expect(screen.getByTestId('home-today-action').textContent).toContain('home.cta_edit_entry');
  });

  it('dispatches logToday from the compact action', async () => {
    const spy = vi.fn();
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: entry, loading: false },
      events: { logToday: spy },
    });

    await fireEvent.click(screen.getByTestId('home-today-action'));
    expect(spy).toHaveBeenCalled();
  });
});
