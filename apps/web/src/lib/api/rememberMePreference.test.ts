import { afterEach, describe, expect, it } from 'vitest';
import {
  REMEMBER_ME_STORAGE_KEY,
  readRememberMePreference,
  writeRememberMePreference,
} from './rememberMePreference';

describe('rememberMePreference', () => {
  afterEach(() => {
    localStorage.removeItem(REMEMBER_ME_STORAGE_KEY);
  });

  it('defaults to true when unset', () => {
    expect(readRememberMePreference()).toBe(true);
  });

  it('round-trips the UX flag only', () => {
    writeRememberMePreference(false);
    expect(localStorage.getItem(REMEMBER_ME_STORAGE_KEY)).toBe('false');
    expect(readRememberMePreference()).toBe(false);
    writeRememberMePreference(true);
    expect(readRememberMePreference()).toBe(true);
  });
});
