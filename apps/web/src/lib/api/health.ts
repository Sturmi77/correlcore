/**
 * Health API client — thin wrapper around GET /health
 *
 * Used by the /status page to display live system state.
 * Never exposes user data — health endpoints are public and contain
 * only infrastructure-level information.
 */

export interface ComponentHealth {
  name: string;
  status: 'ok' | 'degraded' | 'down';
  detail?: string;
}

export interface ReadinessReport {
  status: 'ready' | 'not_ready';
  components: ComponentHealth[];
}

export interface HealthSummary {
  status: 'ok' | 'degraded';
  version: string;
  readiness: ReadinessReport;
}

export interface LivenessResult {
  status: 'ok';
  version: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    signal,
    headers: { Accept: 'application/json' },
  });
  if (!res.ok && res.status !== 503) {
    throw new Error(`Health fetch failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** Full aggregated health summary — always HTTP 200. */
export async function fetchHealthSummary(signal?: AbortSignal): Promise<HealthSummary> {
  return fetchJson<HealthSummary>('/health', signal);
}

/** Liveness only — process alive check, no external deps. */
export async function fetchLiveness(signal?: AbortSignal): Promise<LivenessResult> {
  return fetchJson<LivenessResult>('/health/live', signal);
}
