/**
 * Runtime instance configuration (#734/#735).
 *
 * Loaded once from the public `GET /api/v1/instance` endpoint and cached in a
 * store, so the same web bundle presents a hosted (account-signup) or
 * self-host CTA depending on the deployment it talks to — no build-time flag.
 *
 * The store starts `null` (unknown); consumers fall back to self-host defaults
 * until it resolves. The fetch is fire-and-forget and best-effort: on failure
 * (e.g. anonymous landing with the API briefly unreachable) the store stays
 * null and the self-host default stands.
 */
import { writable } from 'svelte/store';
import { fetchInstanceInfo, type InstanceInfo } from '$lib/api/instance';

export const instanceConfig = writable<InstanceInfo | null>(null);

let started = false;

/** Load the instance descriptor once per session; safe to call repeatedly. */
export async function loadInstanceConfig(): Promise<void> {
  if (started) return;
  started = true;
  try {
    instanceConfig.set(await fetchInstanceInfo());
  } catch {
    // Best-effort: keep null so consumers use the self-host default.
    started = false;
  }
}
