import { render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightMatrix from './InsightMatrix.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
    locale: readable('en'),
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
  it('sorts strong correlations by absolute effect and moves weak ones into the disclosure (#725)', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          // confidence 0.15 sits in the weakened band [0.1, 0.2) — collapsed, not dropped.
          { ...base, id: 'weak', subject_label: 'Weak signal', confidence: 0.15 },
          // confidence 0.05 is below the weak floor — dropped entirely.
          { ...base, id: 'noise', subject_label: 'Noise', confidence: 0.05 },
          { ...base, id: 'small', subject_label: 'Small', effect_size: 0.2 },
          { ...base, id: 'strong', subject_label: 'Strong', effect_size: -0.7 },
        ],
      },
    });

    const strongTable = screen.getByTestId('insight-matrix-table');
    const strongText = within(strongTable)
      .getAllByRole('row')
      .map((row) => row.textContent ?? '');
    expect(strongText.join(' ')).not.toContain('Weak signal');
    expect(strongText.join(' ')).not.toContain('Noise');
    expect(strongText[1]).toContain('Strong');
    expect(strongText[2]).toContain('Small');

    // Weakened row is reachable in the collapsed section instead of vanishing.
    const weakSection = screen.getByTestId('insight-matrix-weak');
    expect(weakSection.textContent).toContain('Weak signal');
    // Sub-weak noise is not shown anywhere.
    expect(screen.queryByText('Noise')).toBeNull();
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

  it('shows tags, habits and symptoms together in one matrix', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          { ...base, id: 'tag', subject_id: 'plain-tag', subject_label: 'Focus', effect_size: 0.3 },
          {
            ...base,
            id: 'habit',
            subject_id: 'habit-tag',
            subject_label: 'Walk',
            effect_size: 0.5,
          },
          {
            ...base,
            id: 'symptom',
            subject_type: 'symptom',
            subject_id: 'symptom-1',
            subject_label: 'Headache',
            effect_size: -0.6,
          },
        ],
      },
    });

    expect(screen.queryByTestId('insight-matrix-layer-tags')).toBeNull();
    expect(screen.queryByTestId('insight-matrix-layer-habits')).toBeNull();
    expect(screen.queryByTestId('insight-matrix-layer-symptoms')).toBeNull();

    const rows = within(screen.getByTestId('insight-matrix')).getAllByRole('row');
    expect(rows).toHaveLength(4);
    expect(rows[1].textContent).toContain('Headache');
    expect(rows[2].textContent).toContain('Walk');
    expect(rows[3].textContent).toContain('Focus');
  });

  it('surfaces a last-updated hint from the newest generated_at (#725)', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          { ...base, id: 'older', subject_label: 'Older', generated_at: '2026-05-10T00:00:00Z' },
          { ...base, id: 'newer', subject_label: 'Newer', generated_at: '2026-05-14T00:00:00Z' },
        ],
      },
    });

    // The hint renders whenever a row carries a generated_at. (The mocked $_
    // echoes the key, so the interpolated date is not part of the visible text.)
    expect(screen.getByTestId('insight-matrix-updated')).toBeTruthy();
  });

  it('hides the last-updated hint in marketing preview mode', () => {
    render(InsightMatrix, {
      props: {
        preview: true,
        insights: [{ ...base, id: 'p', subject_label: 'Preview' }],
      },
    });

    expect(screen.queryByTestId('insight-matrix-updated')).toBeNull();
  });

  it('uses a relative effect bar and drops the wide min-width on mobile CSS', async () => {
    const { readFileSync } = await import('node:fs');
    const { resolve } = await import('node:path');
    const source = readFileSync(
      resolve('src/lib/components/insights/InsightMatrix.svelte'),
      'utf8'
    );
    expect(source).toContain('insight-matrix__effect-bar');
    expect(source).toContain('--effect:');
    expect(source).toContain('@media (max-width: 767px)');
    expect(source).toMatch(/@media \(max-width: 767px\)[\s\S]*min-width:\s*0/);
  });
});
