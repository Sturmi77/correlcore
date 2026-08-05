import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import EntryHistorySheet from './EntryHistorySheet.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

const entry = {
  id: 'entry-1',
  user_id: 'user-1',
  entry_date: '2026-05-16',
  slot: 'day' as const,
  mood_score: 4,
  energy: 3,
  stress: 2,
  cycle_day: null,
  source: 'direct' as const,
  work_context: 'office' as const,
  note: 'Focused day',
  created_at: '2026-05-16T10:00:00Z',
  updated_at: '2026-05-16T10:00:00Z',
};

describe('EntryHistorySheet', () => {
  it('renders read-only entry details with tags and symptoms', () => {
    render(EntryHistorySheet, {
      props: {
        open: true,
        date: '2026-05-16',
        details: [
          {
            entry,
            tags: ['Focus'],
            symptoms: [{ name: 'Headache', intensity: 2 }],
            markers: [],
          },
        ],
      },
    });

    expect(screen.getByTestId('entry-history-sheet')).toBeTruthy();
    expect(screen.getByText('2026-05-16')).toBeTruthy();
    expect(screen.getByText('Focus')).toBeTruthy();
    expect(screen.getByText('Headache (2)')).toBeTruthy();
    expect(screen.getByText('Focused day')).toBeTruthy();
  });

  it('shows a read-only sleep line when the entry has sleep data (#653 B1)', () => {
    render(EntryHistorySheet, {
      props: {
        open: true,
        date: '2026-05-16',
        details: [
          {
            entry: { ...entry, sleep_minutes: 450, sleep_quality: 4 },
            tags: [],
            symptoms: [],
            markers: [],
          },
        ],
      },
    });

    expect(screen.getByTestId('entry-history-sleep')).toBeTruthy();
  });

  it('omits the sleep line when the entry has no sleep data', () => {
    render(EntryHistorySheet, {
      props: {
        open: true,
        date: '2026-05-16',
        details: [{ entry, tags: [], symptoms: [], markers: [] }],
      },
    });

    expect(screen.queryByTestId('entry-history-sleep')).toBeNull();
  });

  it('dispatches close from the close button', async () => {
    const close = vi.fn();
    render(EntryHistorySheet, {
      props: { open: true, date: '2026-05-16', details: [] },
      events: { close },
    });

    await fireEvent.click(screen.getByTestId('entry-history-close'));
    expect(close).toHaveBeenCalledOnce();
  });
});
