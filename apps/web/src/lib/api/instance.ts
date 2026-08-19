/**
 * Public instance descriptor (#734/#735).
 *
 * `GET /api/v1/instance` tells the client whether it is talking to the managed
 * SaaS (`hosted`) or a self-hosted deployment, whether anonymous registration
 * is open, and the running version. The landing uses it to pick the right
 * primary CTA at runtime, so one web bundle serves both modes — no build flag.
 */
import { api } from './client';

export type InstanceMode = 'hosted' | 'selfhost';

export interface InstanceInfo {
  mode: InstanceMode;
  registration_enabled: boolean;
  version: string;
}

/** Fetch the public instance descriptor. Never sends/refreshes auth. */
export function fetchInstanceInfo(): Promise<InstanceInfo> {
  return api.get<InstanceInfo>('/instance', { skipAuthRefresh: true });
}
