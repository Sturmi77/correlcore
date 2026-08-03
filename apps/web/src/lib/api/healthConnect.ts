import { api } from './client';

/** One day's imported sleep duration (M8 Sprint 4, #172). */
export interface HealthConnectSleepImportItem {
  entry_date: string; // ISO date YYYY-MM-DD
  sleep_minutes: number;
}

export interface HealthConnectImportRequest {
  sleep: HealthConnectSleepImportItem[];
}

export interface HealthConnectImportResponse {
  updated: number;
  skipped_existing_value: number;
  skipped_no_entry: number;
  sleep_sync_enabled: boolean;
  /** Dates filled on this import (ISO YYYY-MM-DD). */
  updated_entry_dates?: string[];
  /** Dates skipped because sleep was already set (ISO YYYY-MM-DD). */
  skipped_existing_entry_dates?: string[];
}

/**
 * Import wearable sleep into existing entries. The server enforces the Art. 9
 * consent (403 without it), the per-field toggle, and the manual-wins merge.
 */
export async function importHealthConnectSleep(
  sleep: HealthConnectSleepImportItem[]
): Promise<HealthConnectImportResponse> {
  return api.post<HealthConnectImportResponse>('/health-connect/import', { sleep });
}
