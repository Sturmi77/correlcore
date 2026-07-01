/**
 * Tests for the auth store (Issue #40).
 *
 * The store is a UI mirror of session state held in HttpOnly cookies.
 * We mock the auth API module and assert state transitions only.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

// Mock the API module BEFORE importing the store.
vi.mock('$lib/api/auth', () => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock('$lib/stores/insights', () => ({
  resetInsightStore: vi.fn(),
}));

vi.mock('$lib/offline/session', () => ({
  clearOfflineDataForAnonymousSession: vi.fn(),
  clearOfflineDataForLogout: vi.fn(),
  prepareOfflineDataForAuthenticatedUser: vi.fn(),
}));

import * as authApi from '$lib/api/auth';
import * as offlineSession from '$lib/offline/session';
import { resetInsightStore } from '$lib/stores/insights';
import {
  _resetForTests,
  auth,
  currentUser,
  hydrate,
  isAuthenticated,
  isAuthLoading,
  login,
  logout,
  setUser,
} from './auth';

const fakeUser = {
  id: 'usr_1',
  email: 'a@b.de',
  display_name: 'A',
  is_verified: true,
};

beforeEach(() => {
  _resetForTests();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.resetAllMocks();
});

describe('auth store — initial state', () => {
  it('starts in loading state', () => {
    expect(get(auth)).toEqual({ status: 'loading' });
    expect(get(isAuthLoading)).toBe(true);
    expect(get(isAuthenticated)).toBe(false);
    expect(get(currentUser)).toBeNull();
  });
});

describe('hydrate', () => {
  it('transitions to authenticated when /me returns a user', async () => {
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValueOnce(fakeUser);
    await hydrate();
    expect(get(auth)).toEqual({ status: 'authenticated', user: fakeUser });
    expect(get(currentUser)).toEqual(fakeUser);
    expect(get(isAuthenticated)).toBe(true);
    expect(offlineSession.prepareOfflineDataForAuthenticatedUser).toHaveBeenCalledWith('usr_1');
  });

  it('transitions to anonymous without wiping offline data when /me returns null', async () => {
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValueOnce(null);
    await hydrate();
    expect(get(auth)).toEqual({ status: 'anonymous' });
    expect(get(isAuthenticated)).toBe(false);
    expect(offlineSession.clearOfflineDataForAnonymousSession).not.toHaveBeenCalled();
  });

  it('falls back to anonymous on network error', async () => {
    vi.mocked(authApi.fetchCurrentUser).mockRejectedValueOnce(new Error('network'));
    await hydrate();
    expect(get(auth)).toEqual({ status: 'anonymous' });
    expect(offlineSession.clearOfflineDataForAnonymousSession).not.toHaveBeenCalled();
  });

  it('is idempotent — only calls fetchCurrentUser once', async () => {
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValueOnce(fakeUser);
    await hydrate();
    await hydrate();
    expect(authApi.fetchCurrentUser).toHaveBeenCalledTimes(1);
  });
});

describe('login / logout / setUser', () => {
  it('login updates the store with the returned user', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce({
      access_token: 't',
      token_type: 'bearer',
      expires_in: 900,
      user: fakeUser,
    });
    const user = await login({ email: 'a@b.de', password: 'pw12345678' });
    expect(user).toEqual(fakeUser);
    expect(get(auth)).toEqual({ status: 'authenticated', user: fakeUser });
    expect(offlineSession.prepareOfflineDataForAuthenticatedUser).toHaveBeenCalledWith('usr_1');
    expect(resetInsightStore).toHaveBeenCalledTimes(1);
  });

  it('logout clears state even when API call fails', async () => {
    await setUser(fakeUser);
    expect(get(isAuthenticated)).toBe(true);
    vi.mocked(resetInsightStore).mockClear();
    vi.mocked(authApi.logout).mockRejectedValueOnce(new Error('boom'));
    await logout();
    expect(get(auth)).toEqual({ status: 'anonymous' });
    expect(offlineSession.clearOfflineDataForLogout).toHaveBeenCalledTimes(1);
    expect(resetInsightStore).toHaveBeenCalledTimes(1);
  });

  it('setUser sets authenticated state without an API call', async () => {
    await setUser(fakeUser);
    expect(get(auth)).toEqual({ status: 'authenticated', user: fakeUser });
    expect(offlineSession.prepareOfflineDataForAuthenticatedUser).toHaveBeenCalledWith('usr_1');
    expect(resetInsightStore).toHaveBeenCalledTimes(1);
  });
});
