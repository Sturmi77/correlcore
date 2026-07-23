import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import { LAST_USER_STORAGE_KEY, cacheLastUser, clearLastUser, readLastUser } from './lastUserCache';

const user = {
  id: 'usr_1',
  email: 'a@b.de',
  display_name: 'A',
  is_verified: true,
};

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe('lastUserCache', () => {
  it('round-trips a user snapshot', () => {
    cacheLastUser(user);
    expect(readLastUser()).toEqual(user);
    expect(localStorage.getItem(LAST_USER_STORAGE_KEY)).toContain('usr_1');
  });

  it('rejects malformed payloads', () => {
    localStorage.setItem(LAST_USER_STORAGE_KEY, '{"email":"x"}');
    expect(readLastUser()).toBeNull();
  });

  it('clears the snapshot', () => {
    cacheLastUser(user);
    clearLastUser();
    expect(readLastUser()).toBeNull();
  });
});
