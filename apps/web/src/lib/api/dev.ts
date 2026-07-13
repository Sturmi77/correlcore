import { api } from './client';

export interface DevInfoResponse {
  image_hash: string;
  image_digest: string | null;
  image_tag: string;
  build_time: string | null;
  git_commit: string;
  git_branch: string;
  python_version: string;
  fastapi_version: string;
  db_migration_head: string | null;
  db_pool_size: number | null;
  db_checked_out: number | null;
  redis_connected: boolean;
  minio_connected: boolean;
  health_ready: boolean;
  uptime_seconds: number;
}

export interface WorkerRunResponse {
  id: string;
  worker_name: string;
  job_kind: string;
  trigger_source: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  scope_user_id: string | null;
  result: Record<string, unknown>;
  error_message: string | null;
}

export interface WorkerRunsListResponse {
  items: WorkerRunResponse[];
  ops_ready: boolean;
}

export interface WorkerRunsLatestResponse {
  daily_bundle: WorkerRunResponse | null;
  fleet_insights: WorkerRunResponse | null;
  user_insights: WorkerRunResponse | null;
  ops_ready: boolean;
}

export interface DevInsightsRunResponse {
  status: 'ok';
  eligible_users: number;
  processed_users: number;
  failed_users: number;
  generated_insights: number;
}

export interface DevDbBackupItem {
  name: string;
  size_bytes: number;
  created_at: string;
  meta: Record<string, unknown> | null;
}

export interface DevDbBackupListResponse {
  items: DevDbBackupItem[];
  backup_dir: string;
  ops_ready: boolean;
  encryption_key_required: boolean;
}

export interface DevDbBackupCreateResponse {
  status: 'ok';
  backup: DevDbBackupItem;
  message: string;
}

export interface DevDbRestoreResponse {
  status: 'ok';
  restored: string;
  message: string;
  ops_ready: boolean;
}

export async function fetchDevInfo(signal?: AbortSignal): Promise<DevInfoResponse> {
  return api.get<DevInfoResponse>('/dev/info', { signal });
}

export async function fetchWorkerRuns(options?: {
  limit?: number;
  scope?: 'all' | 'me';
  signal?: AbortSignal;
}): Promise<WorkerRunsListResponse> {
  const params = new URLSearchParams();
  if (options?.limit != null) params.set('limit', String(options.limit));
  if (options?.scope) params.set('scope', options.scope);
  const query = params.toString();
  return api.get<WorkerRunsListResponse>(`/dev/workers${query ? `?${query}` : ''}`, {
    signal: options?.signal,
  });
}

export async function fetchWorkerRunsLatest(
  signal?: AbortSignal
): Promise<WorkerRunsLatestResponse> {
  return api.get<WorkerRunsLatestResponse>('/dev/workers/latest', { signal });
}

export async function runDevInsightsOnce(signal?: AbortSignal): Promise<DevInsightsRunResponse> {
  return api.post<DevInsightsRunResponse>('/dev/workers/insights/run-once', undefined, { signal });
}

export async function fetchDevDbBackups(signal?: AbortSignal): Promise<DevDbBackupListResponse> {
  return api.get<DevDbBackupListResponse>('/dev/db/backups', { signal });
}

export async function createDevDbBackup(signal?: AbortSignal): Promise<DevDbBackupCreateResponse> {
  return api.post<DevDbBackupCreateResponse>('/dev/db/backups', undefined, { signal });
}

export async function restoreDevDbBackup(
  name: string,
  signal?: AbortSignal
): Promise<DevDbRestoreResponse> {
  return api.post<DevDbRestoreResponse>('/dev/db/restore', { name, confirm: true }, { signal });
}
