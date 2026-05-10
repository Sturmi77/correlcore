import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import { fetchDevInfo } from './dev';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('dev API client', () => {
  it('fetches developer information', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      image_hash: 'sha-abc1234',
      image_digest: null,
      image_tag: 'sha-abc1234',
      build_time: null,
      git_commit: 'abc1234',
      git_branch: 'main',
      python_version: '3.12.0',
      fastapi_version: '0.115.0',
      db_migration_head: '010',
      db_pool_size: 5,
      db_checked_out: 0,
      redis_connected: true,
      minio_connected: false,
      health_ready: true,
      uptime_seconds: 12,
    });

    await fetchDevInfo();
    expect(api.get).toHaveBeenCalledWith('/dev/info', { signal: undefined });
  });

  it('passes through an abort signal', async () => {
    const controller = new AbortController();
    vi.mocked(api.get).mockResolvedValueOnce({ image_hash: 'sha-abc1234' });

    await fetchDevInfo(controller.signal);
    expect(api.get).toHaveBeenCalledWith('/dev/info', { signal: controller.signal });
  });
});
