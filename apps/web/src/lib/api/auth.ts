/**
 * Auth API client — Issue #40 + M11 Sprint 3 (ADR-0006).
 *
 * Browser: HttpOnly cookies via apiFetch.
 * Capacitor: opt-in `?include_access_token=true` + in-memory JWT pair.
 */

import { api, apiFetch, ApiError } from './client';
import { usesBearerAuth } from './platform';
import { clearSessionTokens, getRefreshToken, setSessionTokens } from './sessionTokens';

// ---------------------------------------------------------------------------
// Types — mirror backend schemas
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  is_verified: boolean;
}

export interface TokenResponse {
  /** Present only when the API was called with `?include_access_token=true`. */
  access_token?: string;
  /** Present with the same opt-in (Capacitor refresh body). */
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface MessageResponse {
  message: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

function tokenQuery(): string {
  return usesBearerAuth() ? '?include_access_token=true' : '';
}

function stashTokensFromResponse(res: TokenResponse): TokenResponse {
  if (usesBearerAuth()) {
    setSessionTokens(res);
  }
  return res;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** POST /auth/register — schedules a verification email server-side. */
export async function register(payload: RegisterPayload): Promise<MessageResponse> {
  return api.post<MessageResponse>('/auth/register', payload);
}

/** POST /auth/login — cookies (browser) or JWT body (Capacitor). */
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>(`/auth/login${tokenQuery()}`, payload);
  return stashTokensFromResponse(res);
}

/** POST /auth/logout — clears cookies / revokes refresh; clears in-memory tokens. */
export async function logout(): Promise<MessageResponse> {
  const bearer = usesBearerAuth();
  const body = bearer ? { refresh_token: getRefreshToken() } : {};
  try {
    return await api.post<MessageResponse>('/auth/logout', body);
  } finally {
    clearSessionTokens();
  }
}

/** GET /auth/me — returns the currently authenticated user.
 *  Returns null if no valid session exists (401). */
export async function fetchCurrentUser(): Promise<UserResponse | null> {
  try {
    return await api.get<UserResponse>('/auth/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}

/** POST /auth/verify-email — confirms email and establishes a session. */
export async function verifyEmail(token: string): Promise<TokenResponse> {
  const res = await apiFetch<TokenResponse>(`/auth/verify-email${tokenQuery()}`, {
    method: 'POST',
    json: { token },
    skipAuthRefresh: true,
  });
  return stashTokensFromResponse(res);
}

/** POST /auth/resend-verification — always returns 202 (anti-enumeration). */
export async function resendVerification(email: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/auth/resend-verification', {
    method: 'POST',
    json: { email },
    skipAuthRefresh: true,
  });
}

/** POST /auth/forgot-password — always returns 202 (anti-enumeration). */
export async function requestPasswordReset(email: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/auth/forgot-password', {
    method: 'POST',
    json: { email },
    skipAuthRefresh: true,
  });
}

/** POST /auth/reset-password — sets new password and establishes a session. */
export async function resetPassword(payload: {
  token: string;
  password: string;
}): Promise<TokenResponse> {
  const res = await apiFetch<TokenResponse>(`/auth/reset-password${tokenQuery()}`, {
    method: 'POST',
    json: payload,
    skipAuthRefresh: true,
  });
  return stashTokensFromResponse(res);
}
