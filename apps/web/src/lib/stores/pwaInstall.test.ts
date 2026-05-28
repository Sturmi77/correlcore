import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const storage: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => storage[key] ?? null,
  setItem: (key: string, value: string) => {
    storage[key] = value;
  },
  removeItem: (key: string) => {
    delete storage[key];
  },
  clear: () => {
    Object.keys(storage).forEach((key) => delete storage[key]);
  },
};

describe('pwaInstallStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.resetModules();
    vi.stubGlobal('localStorage', localStorageMock);
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn(() => ({ matches: false })),
    });
  });

  it('captures beforeinstallprompt and persists dismissals', async () => {
    const { pwaInstallStore, PWA_DISMISSED_STORAGE_KEY } = await import('./pwaInstall');
    const event = new Event('beforeinstallprompt') as Event & {
      prompt: () => Promise<void>;
      userChoice: Promise<{ outcome: 'dismissed'; platform: string }>;
    };
    event.prompt = vi.fn(async () => undefined);
    event.userChoice = Promise.resolve({ outcome: 'dismissed', platform: 'web' });
    const preventDefault = vi.spyOn(event, 'preventDefault');

    window.dispatchEvent(event);

    expect(preventDefault).toHaveBeenCalledOnce();
    expect(get(pwaInstallStore).promptEvent).toBe(event);

    pwaInstallStore.dismiss();

    expect(localStorage.getItem(PWA_DISMISSED_STORAGE_KEY)).toBe('true');
    expect(get(pwaInstallStore).dismissed).toBe(true);
  });
});
