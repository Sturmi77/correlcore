import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CooccurrenceEntrySheet from './CooccurrenceEntrySheet.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const details = [
  {
    entry: {
      id: 'entry-1',
      user_id: 'user-1',
      entry_date: '2026-05-08',
      slot: 'day' as const,
      mood_score: 4,
      energy: 3,
      stress: 2,
      cycle_day: null,
      source: 'direct' as const,
      work_context: 'homeoffice' as const,
      note: null,
      created_at: '2026-05-08T10:00:00Z',
      updated_at: '2026-05-08T10:00:00Z',
    },
    tags: ['Focus', 'Walk'],
    symptoms: [],
  },
];

describe('CooccurrenceEntrySheet', () => {
  it('renders filtered entries for a tag pair', () => {
    render(CooccurrenceEntrySheet, {
      props: {
        open: true,
        title: 'Focus + Walk',
        loading: false,
        error: '',
        details,
      },
    });

    expect(screen.getByTestId('cooccurrence-entry-sheet')).toBeTruthy();
    expect(screen.getByText('Focus + Walk')).toBeTruthy();
    expect(screen.getByText('2026-05-08')).toBeTruthy();
    expect(screen.getByText('Focus, Walk')).toBeTruthy();
  });

  it('closes when the close button is clicked', async () => {
    const close = vi.fn();
    render(CooccurrenceEntrySheet, {
      props: {
        open: true,
        title: 'Focus + Walk',
        loading: false,
        error: '',
        details,
      },
      events: { close },
    });

    await fireEvent.click(screen.getByTestId('cooccurrence-entry-close'));
    expect(close).toHaveBeenCalled();
  });
});
