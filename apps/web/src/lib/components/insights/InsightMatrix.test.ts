import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightMatrix from './InsightMatrix.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

vi.mock('$lib/stores/tags', async () => {
  const { readable } = await import('svelte/store');

  return {
    tags: readable({
      status: 'ready',
      tags: [
        {
          id: 'habit-tag',
          user_id: 'user-1',
          slug: 'walk',
          name: 'Walk',
          category: 'health',
          icon: null,
          color: null,
          is_default: false,
          is_hidden: false,
          include_in_analytics: true,
          habit_type: 'build',
          target_frequency: 4,
          created_at: '2026-05-12T03:00:00Z',
          updated_at: '2026-05-12T03:00:00Z',
        },
      ],
    }),
    refreshTags: vi.fn(),
  };
});

const base = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'pointbiserial' as const,
  tier: 'developing' as const,
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 'plain-tag',
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.7,
  sample_n: 24,
  statement: 'Sport lines up with higher mood.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('InsightMatrix', () => {
  it('sorts tag correlations by absolute effect and filters low confidence rows', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          { ...base, id: 'low', subject_label: 'Low confidence', confidence: 0.1 },
          { ...base, id: 'small', subject_label: 'Small', effect_size: 0.2 },
          { ...base, id: 'strong', subject_label: 'Strong', effect_size: -0.7 },
        ],
      },
    });

    const table = screen.getByTestId('insight-matrix');
    const text = within(table)
      .getAllByRole('row')
      .map((row) => row.textContent ?? '');
    expect(text.join(' ')).not.toContain('Low confidence');
    expect(text[1]).toContain('Strong');
    expect(text[2]).toContain('Small');
  });

  it('deduplicates default and override tag rows by slug', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          {
            ...base,
            id: 'default-alcohol',
            subject_id: 'default-id',
            subject_label: 'Alcohol',
            effect_size: 0.3,
            payload: { tag_slug: 'alcohol' },
          },
          {
            ...base,
            id: 'override-alcohol',
            subject_id: 'override-id',
            subject_label: 'Alkohol',
            effect_size: 0.6,
            payload: { tag_slug: 'alcohol' },
          },
        ],
      },
    });

    const rows = within(screen.getByTestId('insight-matrix')).getAllByRole('row');
    expect(rows).toHaveLength(2);
    expect(rows[1].textContent).toContain('Alkohol');
    expect(rows[1].textContent).not.toContain('Alcohol');
  });

  it('deduplicates legacy mood metric aliases and normalised tag labels', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          {
            ...base,
            id: 'default-alcohol',
            metric: 'mood_score',
            subject_id: 'default-id',
            subject_label: ' Alkohol ',
            effect_size: 0.3,
          },
          {
            ...base,
            id: 'override-alcohol',
            metric: 'mood',
            subject_id: 'override-id',
            subject_label: 'alkohol',
            effect_size: 0.6,
          },
        ],
      },
    });

    const rows = within(screen.getByTestId('insight-matrix')).getAllByRole('row');
    expect(rows).toHaveLength(2);
    expect(rows[1].textContent).toContain('alkohol');
  });

  it('switches between tag, habit and symptom layers exclusively', async () => {
    render(InsightMatrix, {
      props: {
        insights: [
          { ...base, id: 'tag', subject_id: 'plain-tag', subject_label: 'Focus' },
          {
            ...base,
            id: 'habit',
            subject_id: 'habit-tag',
            subject_label: 'Walk',
          },
          {
            ...base,
            id: 'symptom',
            subject_type: 'symptom',
            subject_id: 'symptom-1',
            subject_label: 'Headache',
          },
        ],
      },
    });

    expect(screen.getByText('Focus')).toBeTruthy();
    expect(screen.queryByText('Walk')).toBeNull();
    expect(screen.queryByText('Headache')).toBeNull();

    await fireEvent.click(screen.getByTestId('insight-matrix-layer-habits'));
    expect(screen.queryByText('Focus')).toBeNull();
    expect(screen.getByText('Walk')).toBeTruthy();

    await fireEvent.click(screen.getByTestId('insight-matrix-layer-symptoms'));
    expect(screen.getByText('Headache')).toBeTruthy();
    expect(screen.queryByText('Walk')).toBeNull();
  });

  it('hides the habit layer and skips the tags fetch when enableHabitLayer is false', async () => {
    const { refreshTags } = await import('$lib/stores/tags');
    render(InsightMatrix, {
      props: {
        insights: [{ ...base, subject_label: 'Focus' }],
        enableHabitLayer: false,
      },
    });

    // Static product-shot mode (landing): no habit tab, no API call.
    expect(screen.getByTestId('insight-matrix-layer-tags')).toBeTruthy();
    expect(screen.getByTestId('insight-matrix-layer-symptoms')).toBeTruthy();
    expect(screen.queryByTestId('insight-matrix-layer-habits')).toBeNull();
    expect(refreshTags).not.toHaveBeenCalled();
  });
});
