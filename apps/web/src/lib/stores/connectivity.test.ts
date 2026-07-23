import { get } from 'svelte/store';
import { describe, expect, it, beforeEach } from 'vitest';
import { connectivity, isEffectivelyOffline } from './connectivity';

beforeEach(() => {
  connectivity._resetForTests();
});

describe('connectivity', () => {
  it('treats browser offline as effectively offline', () => {
    connectivity.setBrowserOnline(false);
    connectivity.markServerReachable(true);
    expect(isEffectivelyOffline()).toBe(true);
  });

  it('treats an unreachable API as effectively offline even when the browser is online', () => {
    connectivity.setBrowserOnline(true);
    connectivity.markServerReachable(false);
    expect(get(connectivity).serverReachable).toBe(false);
    expect(isEffectivelyOffline()).toBe(true);
  });

  it('is online only when the browser is online and the API is reachable', () => {
    connectivity.setBrowserOnline(true);
    connectivity.markServerReachable(true);
    expect(isEffectivelyOffline()).toBe(false);
  });
});
