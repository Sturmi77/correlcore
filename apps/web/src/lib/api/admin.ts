/**
 * Admin-console API client (#677 P3).
 *
 * Mirrors the backend schemas in ``app/schemas/admin.py``. Every route is gated
 * server-side by ``require_admin`` → a 403 ``ApiError`` surfaces for non-admins,
 * which the page turns into a "forbidden" state.
 */

import { api } from './client';

export interface AdminUserListItem {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminUserDetail extends AdminUserListItem {
  updated_at: string;
  entry_count: number;
}

export interface AdminMessageResponse {
  message: string;
}

export interface AdminUsersQuery {
  /** Case-insensitive email substring. */
  query?: string;
  /** ``true`` → only active, ``false`` → only disabled, omitted → all. */
  active?: boolean;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

function buildUsersPath(params: AdminUsersQuery): string {
  const search = new URLSearchParams();
  if (params.query?.trim()) search.set('query', params.query.trim());
  if (typeof params.active === 'boolean') search.set('active', String(params.active));
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  if (typeof params.offset === 'number') search.set('offset', String(params.offset));
  const qs = search.toString();
  return qs ? `/admin/users?${qs}` : '/admin/users';
}

/** GET /admin/users — paginated list with optional email search + active filter. */
export async function fetchAdminUsers(
  params: AdminUsersQuery = {}
): Promise<AdminUserListResponse> {
  return api.get<AdminUserListResponse>(buildUsersPath(params), { signal: params.signal });
}

/** GET /admin/users/{id} — detail incl. entry_count. */
export async function fetchAdminUser(id: string): Promise<AdminUserDetail> {
  return api.get<AdminUserDetail>(`/admin/users/${id}`);
}

/** PATCH /admin/users/{id}/active — disable (false) / enable (true). */
export async function setAdminUserActive(id: string, isActive: boolean): Promise<AdminUserDetail> {
  return api.patch<AdminUserDetail>(`/admin/users/${id}/active`, { is_active: isActive });
}

/** DELETE /admin/users/{id} — DSGVO Art. 17 hard-delete (irreversible). */
export async function deleteAdminUser(id: string): Promise<void> {
  await api.delete<void>(`/admin/users/${id}`);
}

/** POST /admin/users/{id}/password-reset — send the user a reset email. */
export async function triggerAdminPasswordReset(id: string): Promise<AdminMessageResponse> {
  return api.post<AdminMessageResponse>(`/admin/users/${id}/password-reset`);
}
