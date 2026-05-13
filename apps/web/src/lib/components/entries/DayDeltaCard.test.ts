import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DayDeltaCard from './DayDeltaCard.svelte';
import type { EntryDeltaResponse } from '$lib/api/entries';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const base: EntryDeltaResponse = {
  today: {
    entry_date: '2026-05-13',
    slot: 'day',
    mood_score: 4,
    energy: 2,
    stress: 3,
  },
  previous: {
    entry_date: '2026-05-12',
    slot: 'day',
    mood_score: 3,
    energy: 4,
    stress: 3,
  },
  delta: { mood: 1, energy: -2, stress: 0 },
  shared_tags: [
    {
      id: 'tag-1',
      user_id: 'user-1',
      slug: 'sport',
      name: 'Sport',
      category: 'sport',
      icon: null,
      color: null,
      is_default: false,
      is_hidden: false,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    },
  ],
};

describe('DayDeltaCard', () => {
  it('renders neutral metric deltas and shared tags', () => {
    render(DayDeltaCard, { props: { delta: base } });

    expect(screen.getByText('entry.delta.heading')).toBeTruthy();
    expect(screen.getByText('+1')).toBeTruthy();
    expect(screen.getByText('-2')).toBeTruthy();
    expect(screen.getByText('0')).toBeTruthy();
    expect(screen.getByText('Sport')).toBeTruthy();
  });

  it('does not render when previous entry is missing', () => {
    const { container } = render(DayDeltaCard, {
      props: { delta: { ...base, previous: null, shared_tags: [] } },
    });

    expect(container.querySelector('[data-testid="day-delta-card"]')).toBeNull();
  });
});
