import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listLatestInsights, type InsightResponse } from '$lib/api/insights';
import { exportMatrixPdf } from '$lib/utils/insightMatrixExport';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const pageUrl = vi.hoisted(() => ({ value: 'http://localhost/insights/report' }));

vi.mock('$app/stores', async () => {
  const { readable } = await import('svelte/store');
  return {
    page: readable({
      get url() {
        return new URL(pageUrl.value);
      },
    }),
  };
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

vi.mock('$lib/utils/insightMatrixExport', () => ({
  exportMatrixPdf: vi.fn(),
  exportMatrixPng: vi.fn(),
  exportReportCsv: vi.fn(),
  exportReportJson: vi.fn(),
  reportExportFilename: (kind: string) => `correlcore-report.${kind}`,
}));

const refreshHandlers = vi.hoisted(() => [] as (() => void)[]);

vi.mock('$lib/stores/pageRefresh', () => ({
  registerPageRefresh: (handler: () => void) => {
    refreshHandlers.push(handler);
    return () => {};
  },
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
  refreshHandlers.length = 0;
  pageUrl.value = 'http://localhost/insights/report';
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

  it('preselects only the requested ?signal= row', async () => {
    pageUrl.value = 'http://localhost/insights/report?signal=b';
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-row-b')).toBeTruthy());
    const checked = Array.from(
      container.querySelectorAll<HTMLInputElement>('[data-testid^="insight-report-row-"] input')
    ).filter((box) => box.checked);

    expect(checked).toHaveLength(1);
    expect(
      checked[0]?.closest('[data-testid^="insight-report-row-"]')?.getAttribute('data-testid')
    ).toBe('insight-report-row-b');
  });

  it('does not refill an emptied selection when the page refreshes', async () => {
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());
    const selectAll = screen.getByTestId('insight-report-select-all') as HTMLInputElement;
    selectAll.checked = false;
    selectAll.dispatchEvent(new Event('change', { bubbles: true }));

    await waitFor(() => expect(selectAll.checked).toBe(false));

    // The refresh hook reloads the same rows. Seeding is one-shot, so the
    // user's empty selection has to survive it.
    expect(refreshHandlers.length).toBeGreaterThan(0);
    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(listLatestInsights).toHaveBeenCalledTimes(2));

    const rowBoxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('[data-testid^="insight-report-row-"] input')
    );
    expect(rowBoxes.length).toBeGreaterThan(0);
    expect(rowBoxes.every((box) => !box.checked)).toBe(true);
  });

  it('keeps an untouched selection through a failed refresh', async () => {
    // Clearing `insights` in the catch made the pruning block drop every
    // selected id; seeding is one-shot, so the next success left the table
    // unchecked and every export reported export_empty (#959 review).
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());

    vi.mocked(listLatestInsights).mockRejectedValueOnce(new Error('offline'));
    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(listLatestInsights).toHaveBeenCalledTimes(2));

    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(listLatestInsights).toHaveBeenCalledTimes(3));

    await waitFor(() => {
      const rowBoxes = Array.from(
        container.querySelectorAll<HTMLInputElement>('[data-testid^="insight-report-row-"] input')
      );
      expect(rowBoxes.length).toBeGreaterThan(0);
      expect(rowBoxes.every((box) => box.checked)).toBe(true);
    });
  });

  it('still exports the last loaded rows after a failed refresh, with the error shown', async () => {
    // Keeping stale rows means an export can now run while the error alert is
    // up. That is deliberate: the rows come from a load that succeeded, and a
    // network blip should not cost the user the report they can see. The alert
    // is what says the data may not be the newest.
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());

    vi.mocked(listLatestInsights).mockRejectedValueOnce(new Error('offline'));
    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(container.textContent).toContain('offline'));

    screen
      .getByTestId('insight-report-export-pdf')
      .dispatchEvent(new MouseEvent('click', { bubbles: true }));

    await waitFor(() => expect(exportMatrixPdf).toHaveBeenCalledTimes(1));
    expect(vi.mocked(exportMatrixPdf).mock.calls[0]?.[0]).toHaveLength(2);
    expect(container.textContent).not.toContain('insights.report.export_empty');
  });

  it('hands the PDF export the charset note, so a lossy label can explain itself', async () => {
    // The note only prints when a character was actually replaced, but the
    // builder can only print what the page passes in (#960).
    render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-export-pdf')).toBeTruthy());
    screen
      .getByTestId('insight-report-export-pdf')
      .dispatchEvent(new MouseEvent('click', { bubbles: true }));

    await waitFor(() => expect(exportMatrixPdf).toHaveBeenCalledTimes(1));
    expect(vi.mocked(exportMatrixPdf).mock.calls[0]?.[1]).toMatchObject({
      charsetNote: 'insights.report.pdf_charset_note',
    });
  });

  it('does not re-seed after a failed reload followed by a successful one', async () => {
    const { container } = render(Page);

    await waitFor(() => expect(screen.getByTestId('insight-report-select-all')).toBeTruthy());
    const selectAll = screen.getByTestId('insight-report-select-all') as HTMLInputElement;
    selectAll.checked = false;
    selectAll.dispatchEvent(new Event('change', { bubbles: true }));
    await waitFor(() => expect(selectAll.checked).toBe(false));

    // The catch path clears `insights`, so the next success re-populates the
    // rows from scratch. Seeding still must not fire a second time.
    vi.mocked(listLatestInsights).mockRejectedValueOnce(new Error('offline'));
    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(listLatestInsights).toHaveBeenCalledTimes(2));

    refreshHandlers.forEach((handler) => handler());
    await waitFor(() => expect(listLatestInsights).toHaveBeenCalledTimes(3));

    await waitFor(() => {
      const rowBoxes = Array.from(
        container.querySelectorAll<HTMLInputElement>('[data-testid^="insight-report-row-"] input')
      );
      expect(rowBoxes.length).toBeGreaterThan(0);
      expect(rowBoxes.every((box) => !box.checked)).toBe(true);
    });
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
