import { describe, expect, it } from 'vitest';
import {
  fallbackHealthComponents,
  healthStatusTone,
  insightWorkerIsOverdue,
  insightWorkerNeverRan,
  resolveHealthComponents,
  selectFaultyHomeContainers,
} from './devHealth';
import type { DevInfoResponse } from '$lib/api/dev';

const baseInfo: DevInfoResponse = {
  image_hash: 'sha',
  image_digest: null,
  image_tag: 'sha',
  build_time: null,
  git_commit: 'abc',
  git_branch: 'main',
  python_version: '3.12',
  fastapi_version: '0.1',
  db_migration_head: null,
  db_pool_size: null,
  db_checked_out: null,
  redis_connected: true,
  minio_connected: false,
  health_ready: true,
  uptime_seconds: 1,
};

describe('devHealth', () => {
  it('maps probe statuses to UI tones', () => {
    expect(healthStatusTone('ok')).toBe('ok');
    expect(healthStatusTone('degraded')).toBe('warn');
    expect(healthStatusTone('unavailable')).toBe('muted');
    expect(healthStatusTone('down')).toBe('down');
    expect(healthStatusTone('unknown')).toBe('down');
  });

  it('falls back to the legacy aggregate chips', () => {
    expect(
      fallbackHealthComponents({
        health_ready: true,
        redis_connected: false,
        minio_connected: true,
      })
    ).toEqual([
      { name: 'health', status: 'ok' },
      { name: 'redis', status: 'down' },
      { name: 'minio', status: 'ok' },
    ]);
  });

  it('prefers API health_components when present', () => {
    const components = [{ name: 'postgres', status: 'ok' as const }];
    expect(
      resolveHealthComponents({
        health_ready: true,
        redis_connected: true,
        minio_connected: false,
        health_components: components,
      })
    ).toBe(components);
  });

  it('treats missing and never_run insight jobs as never ran', () => {
    expect(insightWorkerNeverRan(null)).toBe(true);
    expect(insightWorkerNeverRan({ status: 'never_run', finished_at: null })).toBe(true);
    expect(
      insightWorkerNeverRan({ status: 'succeeded', finished_at: '2026-09-07T03:00:00Z' })
    ).toBe(false);
  });

  it('treats a missed nightly cadence as overdue', () => {
    const now = new Date('2026-09-08T12:00:00Z');
    expect(insightWorkerIsOverdue(null, now)).toBe(true);
    expect(
      insightWorkerIsOverdue({ status: 'succeeded', finished_at: '2026-09-07T03:00:00Z' }, now)
    ).toBe(true);
    expect(
      insightWorkerIsOverdue({ status: 'succeeded', finished_at: '2026-09-07T10:00:00Z' }, now)
    ).toBe(false);
  });

  it('uses Docker issue flags and skips a clean migrate exit', () => {
    expect(
      selectFaultyHomeContainers({
        ...baseInfo,
        containers: [
          {
            name: 'correlcore-migrate',
            service: 'migrate',
            state: 'exited',
            health: 'none',
            exit_code: 0,
            issue: 'none',
          },
          {
            name: 'correlcore-worker',
            service: 'worker',
            state: 'exited',
            health: 'none',
            exit_code: 137,
            issue: 'stopped',
          },
          {
            name: 'correlcore-postgres',
            service: 'postgres',
            state: 'running',
            health: 'unhealthy',
            issue: 'unhealthy',
          },
        ],
      })
    ).toEqual([
      { name: 'worker', issue: 'stopped' },
      { name: 'postgres', issue: 'unhealthy' },
    ]);
  });

  it('falls back to down probes and ignores unresolved optional services', () => {
    expect(
      selectFaultyHomeContainers({
        ...baseInfo,
        health_components: [
          { name: 'api', status: 'ok' },
          { name: 'encryption', status: 'ok' },
          { name: 'postgres', status: 'down', detail: 'OperationalError' },
          { name: 'worker', status: 'down', detail: 'stopped' },
          { name: 'minio', status: 'down', detail: 'unresolved' },
        ],
      })
    ).toEqual([
      { name: 'postgres', issue: 'unhealthy' },
      { name: 'worker', issue: 'stopped' },
    ]);
  });

  it('keeps probe faults for services missing from a partial Docker list', () => {
    expect(
      selectFaultyHomeContainers({
        ...baseInfo,
        containers: [
          {
            name: 'correlcore-postgres',
            service: 'postgres',
            state: 'running',
            health: 'healthy',
            issue: 'none',
          },
        ],
        health_components: [
          { name: 'postgres', status: 'ok' },
          { name: 'worker', status: 'down', detail: 'stopped' },
        ],
      })
    ).toEqual([{ name: 'worker', issue: 'stopped' }]);
  });
});
