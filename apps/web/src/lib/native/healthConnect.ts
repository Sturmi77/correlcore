/**
 * Web bridge to the native HealthConnect Capacitor plugin (M8 Sprint 3, #172,
 * ADR-0042). Android-only and no-op on browser builds.
 *
 * The plugin reads **only** sleep + heart-rate records; that limit is enforced
 * natively (see HealthConnectPlugin.kt). Every read here is additionally gated
 * behind the DSGVO Art. 9 consent via {@link canUseHealthConnectImport}.
 * Writing imported values into entries is Sprint 4 — this module only exposes
 * availability, permissions, and raw reads.
 */

import type { ConsentListResponse } from '$lib/api/consents';
import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
import { isCapacitorBuild } from '$lib/api/platform';

export interface HealthConnectAvailability {
  available: boolean;
  status?: number;
}

export interface HealthConnectPermissionState {
  granted: boolean;
  available: boolean;
}

export interface HealthConnectSleepRecord {
  startTime: string;
  endTime: string;
  durationMinutes: number;
}

export interface HealthConnectHeartRateRecord {
  startTime: string;
  endTime: string;
  sampleCount: number;
  avgBpm?: number;
  minBpm?: number;
  maxBpm?: number;
}

export interface HealthConnectReadResult {
  sleep: HealthConnectSleepRecord[];
  heartRate: HealthConnectHeartRateRecord[];
}

type HealthConnectPlugin = {
  isAvailable(): Promise<HealthConnectAvailability>;
  checkPermissions(): Promise<HealthConnectPermissionState>;
  requestPermissions(): Promise<HealthConnectPermissionState>;
  readSleepAndHeartRate(options: { start: string; end: string }): Promise<HealthConnectReadResult>;
};

function getNativePlugin(): HealthConnectPlugin | null {
  if (typeof window === 'undefined') return null;
  const cap = (
    window as unknown as {
      Capacitor?: { Plugins?: Record<string, HealthConnectPlugin> };
    }
  ).Capacitor;
  return cap?.Plugins?.HealthConnect ?? null;
}

/** True only inside the Android app with the native plugin present. */
export function isHealthConnectBridgePresent(): boolean {
  return isCapacitorBuild() && getNativePlugin() !== null;
}

/** Whether Health Connect itself is installed/available on this device. */
export async function isHealthConnectAvailable(): Promise<HealthConnectAvailability> {
  const plugin = isCapacitorBuild() ? getNativePlugin() : null;
  if (!plugin) return { available: false };
  try {
    return await plugin.isAvailable();
  } catch {
    return { available: false };
  }
}

/** Current grant state for the fixed sleep + heart-rate read permissions. */
export async function checkHealthConnectPermissions(): Promise<HealthConnectPermissionState> {
  const plugin = isCapacitorBuild() ? getNativePlugin() : null;
  if (!plugin) return { granted: false, available: false };
  try {
    return await plugin.checkPermissions();
  } catch {
    return { granted: false, available: false };
  }
}

/**
 * Launch the Health Connect permission sheet. Requires that the user has already
 * granted the server-side Art. 9 consent — otherwise this refuses without opening
 * the native sheet.
 */
export async function requestHealthConnectPermissions(
  consents: ConsentListResponse | null | undefined
): Promise<HealthConnectPermissionState> {
  if (!canUseHealthConnectImport(consents)) {
    return { granted: false, available: false };
  }
  const plugin = isCapacitorBuild() ? getNativePlugin() : null;
  if (!plugin) return { granted: false, available: false };
  try {
    return await plugin.requestPermissions();
  } catch {
    return { granted: false, available: false };
  }
}

/**
 * Read sleep + heart-rate records in [start, end]. Returns null when consent is
 * missing, the bridge is absent (browser build), or the read fails. `start` and
 * `end` are ISO-8601 instants.
 */
export async function readHealthConnectSleepAndHeartRate(
  consents: ConsentListResponse | null | undefined,
  range: { start: string; end: string }
): Promise<HealthConnectReadResult | null> {
  if (!canUseHealthConnectImport(consents)) return null;
  const plugin = isCapacitorBuild() ? getNativePlugin() : null;
  if (!plugin) return null;
  try {
    return await plugin.readSleepAndHeartRate(range);
  } catch {
    return null;
  }
}
