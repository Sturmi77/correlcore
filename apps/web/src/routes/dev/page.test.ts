import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import Page from './+page.svelte';
import { devMode } from '$lib/stores/devMode';
import { ApiError } from '$lib/api/client';
import type { DevInfoResponse } from '$lib/api/dev';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key), locale: readable('en') };
});

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

const { fetchDevInfo, fetchWorkerRunsLatest, fetchWorkerRuns, fetchDevDbBackups } = vi.hoisted(
  () => ({
    fetchDevInfo: vi.fn(),
    fetchWorkerRunsLatest: vi.fn(),
    fetchWorkerRuns: vi.fn(),
    fetchDevDbBackups: vi.fn(),
  })
);

vi.mock('$lib/api/dev', () => ({
  fetchDevInfo,
  fetchWorkerRunsLatest,
  fetchWorkerRuns,
  fetchDevDbBackups,
  createDevDbBackup: vi.fn(),
  restoreDevDbBackup: vi.fn(),
  runDevInsightsOnce: vi.fn(),
}));

vi.mock('$lib/api/insights', () => ({ regenerateInsights: vi.fn() }));

function mockBackendUnavailable(): void {
  fetchDevInfo.mockRejectedValue(new ApiError(404, 'not found', '/dev/info'));
  fetchWorkerRunsLatest.mockResolvedValue({});
  fetchWorkerRuns.mockResolvedValue({ items: [] });
  fetchDevDbBackups.mockResolvedValue({ items: [], backup_dir: '' });
}

const sampleInfo: DevInfoResponse = {
  image_hash: 'sha-26c4274',
  image_digest: null,
  image_tag: 'sha-26c4274',
  build_time: '2026-05-10T16:00:00Z',
  git_commit: '26c4274e0b2688931f7ceab108d72b775233fdf7',
  git_branch: 'main',
  python_version: '3.12.13',
  fastapi_version: '0.115.0',
  db_migration_head: '009',
  db_pool_size: 10,
  db_checked_out: 1,
  redis_connected: true,
  minio_connected: false,
  health_ready: true,
  uptime_seconds: 42,
  health_components: [
    { name: 'api', status: 'ok', detail: 'process' },
    { name: 'postgres', status: 'ok' },
    { name: 'redis', status: 'ok' },
    { name: 'encryption', status: 'ok' },
    { name: 'minio', status: 'down', detail: 'unresolved' },
  ],
};

describe('/dev consolidation (#695)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBackendUnavailable();
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

  it('renders per-service health chips on the runtime tab', async () => {
    fetchDevInfo.mockResolvedValue(sampleInfo);
    fetchWorkerRunsLatest.mockResolvedValue({
      daily_bundle: null,
      fleet_insights: null,
      user_insights: null,
    });
    fetchWorkerRuns.mockResolvedValue({ items: [] });
    fetchDevDbBackups.mockResolvedValue({ items: [], backup_dir: '/tmp' });

    render(Page);
    await fireEvent.click(await screen.findByTestId('dev-tab-runtime'));

    expect(await screen.findByTestId('dev-health-components')).toBeTruthy();
    expect(screen.getByTestId('dev-health-postgres')).toBeTruthy();
    expect(screen.getByTestId('dev-health-redis')).toBeTruthy();
    expect(screen.getByTestId('dev-health-encryption')).toBeTruthy();
    expect(screen.getByTestId('dev-health-minio').textContent).toContain('unresolved');
  });

  it('renders Docker container state on the runtime tab', async () => {
    fetchDevInfo.mockResolvedValue({
      ...sampleInfo,
      containers: [
        {
          name: 'correlcore-worker',
          service: 'worker',
          state: 'exited',
          health: 'none',
          exit_code: 137,
          issue: 'stopped',
          status_text: 'Exited (137) 4 minutes ago',
        },
      ],
    });
    fetchWorkerRunsLatest.mockResolvedValue({
      daily_bundle: null,
      fleet_insights: null,
      user_insights: null,
    });
    fetchWorkerRuns.mockResolvedValue({ items: [] });
    fetchDevDbBackups.mockResolvedValue({ items: [], backup_dir: '/tmp' });

    render(Page);
    await fireEvent.click(await screen.findByTestId('dev-tab-runtime'));

    expect(await screen.findByTestId('dev-containers')).toBeTruthy();
    expect(screen.getByTestId('dev-container-worker').textContent).toContain('stopped');
  });
});
