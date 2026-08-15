import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import Page from './+page.svelte';
import { devMode } from '$lib/stores/devMode';
import { ApiError } from '$lib/api/client';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key), locale: readable('en') };
});

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// Backend endpoint disabled (404) — the client-only Dev-Visualization tab must
// still work, which is the whole point of #695.
vi.mock('$lib/api/dev', () => ({
  fetchDevInfo: vi.fn(async () => {
    throw new ApiError(404, 'not found', '/dev/info');
  }),
  fetchWorkerRunsLatest: vi.fn(async () => ({})),
  fetchWorkerRuns: vi.fn(async () => ({ items: [] })),
  fetchDevDbBackups: vi.fn(async () => ({ items: [], backup_dir: '' })),
  createDevDbBackup: vi.fn(),
  restoreDevDbBackup: vi.fn(),
  runDevInsightsOnce: vi.fn(),
}));

vi.mock('$lib/api/insights', () => ({ regenerateInsights: vi.fn() }));

describe('/dev consolidation (#695)', () => {
  beforeEach(() => {
    // Reachable because client dev mode is on (7×-tap equivalent).
    devMode.set(true);
  });

  it('renders section tabs including Dev visualization', async () => {
    render(Page);
    expect(await screen.findByTestId('dev-tabs')).toBeTruthy();
    expect(screen.getByTestId('dev-tab-version')).toBeTruthy();
    expect(screen.getByTestId('dev-tab-workers')).toBeTruthy();
    expect(screen.getByTestId('dev-tab-devviz')).toBeTruthy();
  });

  it('exposes the moved client dev controls on the Dev-visualization tab', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('dev-tab-devviz'));

    expect(await screen.findByTestId('developer-toggle')).toBeTruthy();
    expect(screen.getByTestId('force-viz-toggle')).toBeTruthy();
    expect(screen.getByTestId('developer-phase-select')).toBeTruthy();
  });

  it('applies the selected developer phase preset entry count', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('dev-tab-devviz'));

    const phaseSelect = await screen.findByTestId('developer-phase-select');
    await fireEvent.change(phaseSelect, { target: { value: 'robust' } });
    await fireEvent.click(screen.getByText('settings.developer.advanced'));

    await waitFor(() => {
      expect((screen.getByTestId('developer-entry-count') as HTMLInputElement).value).toBe('42');
    });
  });
});
