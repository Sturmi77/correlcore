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

export async function fetchDevInfo(signal?: AbortSignal): Promise<DevInfoResponse> {
  return api.get<DevInfoResponse>('/dev/info', { signal });
}
