/**
 * Browser logout must hit /auth/refresh/logout so the path-scoped
 * refresh_token cookie is attached and Redis can revoke the JTI.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { postMock, usesBearerAuthMock, getRefreshTokenMock, clearSessionTokensMock } = vi.hoisted(
  () => ({
    postMock: vi.fn(),
    usesBearerAuthMock: vi.fn(),
    getRefreshTokenMock: vi.fn(),
    clearSessionTokensMock: vi.fn(),
  })
);

vi.mock('./client', () => ({
  api: { post: postMock },
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

vi.mock('./platform', () => ({
  usesBearerAuth: usesBearerAuthMock,
}));

vi.mock('./sessionTokens', () => ({
  clearSessionTokens: clearSessionTokensMock,
  getRefreshToken: getRefreshTokenMock,
  setSessionTokens: vi.fn(),
}));

import { logout } from './auth';

describe('logout()', () => {
  beforeEach(() => {
    postMock.mockReset();
    usesBearerAuthMock.mockReset();
    getRefreshTokenMock.mockReset();
    clearSessionTokensMock.mockReset();
    postMock.mockResolvedValue({ message: 'Logged out successfully' });
  });

  it('browser path posts to /auth/refresh/logout without a body token', async () => {
    usesBearerAuthMock.mockReturnValue(false);
    await logout();
    expect(postMock).toHaveBeenCalledWith('/auth/refresh/logout', {});
    expect(clearSessionTokensMock).toHaveBeenCalledTimes(1);
  });

  it('Capacitor path posts body refresh_token to /auth/logout', async () => {
    usesBearerAuthMock.mockReturnValue(true);
    getRefreshTokenMock.mockReturnValue('native-refresh');
    await logout();
    expect(postMock).toHaveBeenCalledWith('/auth/logout', {
      refresh_token: 'native-refresh',
    });
    expect(clearSessionTokensMock).toHaveBeenCalledTimes(1);
  });
});
