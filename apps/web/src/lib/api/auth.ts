/**
 * Auth API client — Issue #40.
 *
 * Mirrors the FastAPI shapes in backend/app/schemas/auth.py.
 * All calls use HttpOnly cookies via apiFetch (credentials: 'include').
 */

import { api, apiFetch, ApiError } from './client';

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
  access_token: string;
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

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** POST /auth/register — schedules a verification email server-side. */
export async function register(payload: RegisterPayload): Promise<MessageResponse> {
  return api.post<MessageResponse>('/auth/register', payload);
}

/** POST /auth/login — sets HttpOnly cookies on success. */
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  return api.post<TokenResponse>('/auth/login', payload);
}

/** POST /auth/logout — clears HttpOnly cookies and revokes refresh in Redis. */
export async function logout(): Promise<MessageResponse> {
  return api.post<MessageResponse>('/auth/logout', {});
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

/** POST /auth/verify-email — confirms a user's email via the token from mail. */
export async function verifyEmail(token: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/auth/verify-email', {
    method: 'POST',
    json: { token },
    skipAuthRefresh: true, // verify is a public endpoint
  });
}

/** POST /auth/resend-verification — always returns 202 (anti-enumeration). */
export async function resendVerification(email: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/auth/resend-verification', {
    method: 'POST',
    json: { email },
    skipAuthRefresh: true, // public endpoint
  });
}
