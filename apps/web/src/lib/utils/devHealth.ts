import type { DevHealthComponent, DevInfoResponse } from '$lib/api/dev';

export type DevHealthTone = 'ok' | 'warn' | 'down' | 'muted';

export interface FaultyHomeContainer {
  name: string;
  issue: 'unhealthy' | 'stopped';
}

const HOME_PROBE_SKIP = new Set(['api', 'encryption', 'health']);

export function healthStatusTone(status: string): DevHealthTone {
  if (status === 'ok') return 'ok';
  if (status === 'degraded') return 'warn';
  if (status === 'unavailable') return 'muted';
  return 'down';
}

export function insightWorkerNeverRan(
  run: { status: string; finished_at?: string | null } | null | undefined
): boolean {
  return !run || run.status === 'never_run' || !run.finished_at;
}

/**
 * Nightly USER_INSIGHTS cadence is ~24h (03:00 UTC). 30h matches
 * ``WORKER_STALE_AFTER_HOURS`` so Home container warnings fire after a missed
 * scheduled run, before a second night is at risk — tighter than the 40h
 * end-user InsightFeed banner.
 */
export const INSIGHT_WORKER_STALE_AFTER_HOURS = 30;

export function insightWorkerIsOverdue(
  run: { status: string; finished_at?: string | null } | null | undefined,
  now: Date = new Date()
): boolean {
  if (insightWorkerNeverRan(run)) return true;
  const finished = new Date(run.finished_at as string);
  if (Number.isNaN(finished.getTime())) return true;
  const ageMs = now.getTime() - finished.getTime();
  return ageMs >= INSIGHT_WORKER_STALE_AFTER_HOURS * 60 * 60 * 1000;
}

export function selectFaultyHomeContainers(info: DevInfoResponse): FaultyHomeContainer[] {
  if (info.containers?.length) {
    return info.containers
      .filter((container) => container.issue === 'unhealthy' || container.issue === 'stopped')
      .map((container) => ({
        name: container.service || container.name,
        issue: container.issue,
      }));
  }
  return (info.health_components ?? [])
    .filter((component) => !HOME_PROBE_SKIP.has(component.name))
    .filter((component) => component.status === 'down' || component.status === 'degraded')
    .filter((component) => component.detail !== 'unresolved')
    .map((component) => ({
      name: component.name,
      issue: component.detail === 'stopped' ? 'stopped' : 'unhealthy',
    }));
}

export function resolveHealthComponents(
  info: Pick<DevInfoResponse, 'health_ready' | 'redis_connected' | 'minio_connected'> & {
    health_components?: DevHealthComponent[] | null;
  }
): DevHealthComponent[] {
  if (info.health_components?.length) return info.health_components;
  return fallbackHealthComponents(info);
}

export function fallbackHealthComponents(
  info: Pick<DevInfoResponse, 'health_ready' | 'redis_connected' | 'minio_connected'>
): DevHealthComponent[] {
  return [
    { name: 'health', status: info.health_ready ? 'ok' : 'down' },
    { name: 'redis', status: info.redis_connected ? 'ok' : 'down' },
    { name: 'minio', status: info.minio_connected ? 'ok' : 'down' },
  ];
}
