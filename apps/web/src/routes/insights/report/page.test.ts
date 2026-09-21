import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listLatestInsights, type InsightResponse } from '$lib/api/insights';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

vi.mock('$app/stores', async () => {
  const { readable } = await import('svelte/store');
  return { page: readable({ url: new URL('http://localhost/insights/report') }) };
});

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({ status: 'authenticated', user: { id: 'user-1', email: 'u@example.com' } }),
  };
});

vi.mock('$lib/api/insights', () => ({
  listLatestInsights: vi.fn(),
}));

function matrixRow(id: string): InsightResponse {
  return {
    id,
    user_id: 'user-1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: id,
    subject_label: `Tag ${id}`,
    effect_size: 0.4,
    confidence: 0.7,
    sample_n: 24,
    statement: 'Lines up with higher mood.',
    flags: {},
    payload: {},
    generated_for_date: '2026-05-12',
    generated_at: '2026-05-12T03:00:00Z',
    created_at: '2026-05-12T03:00:00Z',
    updated_at: '2026-05-12T03:00:00Z',
  } as InsightResponse;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listLatestInsights).mockResolvedValue({
    insight_maturity: null,
    insights: [matrixRow('a'), matrixRow('b')],
  } as unknown as Awaited<ReturnType<typeof listLatestInsights>>);
});

describe('/insights/report selection (#959)', () => {
  it('asks the API for the report families so the row cap applies inside them', async () => {
    render(Page);

    await waitFor(() => expect(listLatestInsights).toHaveBeenCalled());
    expect(listLatestInsights).toHaveBeenCalledWith({
      limit: 50,
      insightTypes: ['pointbiserial', 'symptom_mood_association'],
    });
  });

  it('selects every row on first load', async () => {
    render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());
    const selectAll = screen.getByTestId('insight-report-select-all') as HTMLInputElement;
    expect(selectAll.checked).toBe(true);
  });

  it('keeps a deliberately emptied selection empty and surfaces export_empty', async () => {
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());
    const selectAll = screen.getByTestId('insight-report-select-all') as HTMLInputElement;

    // Unticking "select all" used to refill instantly: the reactive block read
    // any empty selection as "not initialised yet", so the last row could not be
    // removed and the export_empty path was unreachable after load.
    selectAll.checked = false;
    selectAll.dispatchEvent(new Event('change', { bubbles: true }));

    await waitFor(() => {
      const rowBoxes = Array.from(
        container.querySelectorAll<HTMLInputElement>('[data-testid^="insight-report-row-"] input')
      );
      expect(rowBoxes.length).toBeGreaterThan(0);
      expect(rowBoxes.every((box) => !box.checked)).toBe(true);
    });

    const pdfButton = screen.getByTestId('insight-report-export-pdf');
    pdfButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    await waitFor(() => expect(container.textContent).toContain('insights.report.export_empty'));
  });
});
