import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { createPwaLifecycleStore } from './pwaLifecycle';

function makeEnvironment(options: { online?: boolean; waiting?: boolean } = {}) {
  const worker = { postMessage: vi.fn() };
  const registrationTarget = new EventTarget();
  const registration = Object.assign(registrationTarget, {
    waiting: options.waiting ? worker : null,
    installing: null,
    update: vi.fn(async () => undefined),
  }) as unknown as ServiceWorkerRegistration;
  const serviceWorkerTarget = new EventTarget();
  const serviceWorker = Object.assign(serviceWorkerTarget, {
    controller: {},
    ready: Promise.resolve(registration),
  });
  const navigator = {
    onLine: options.online ?? true,
    serviceWorker,
  } as unknown as Navigator;
  const windowTarget = new EventTarget();
  const fakeWindow = Object.assign(windowTarget, {
    location: { reload: vi.fn() },
  }) as unknown as Window;

  return { navigator, window: fakeWindow, registration, worker };
}

describe('pwaLifecycle', () => {
  it('tracks browser connection changes', () => {
    const env = makeEnvironment({ online: false });
    const store = createPwaLifecycleStore(env);
    store.initialize();

    expect(get(store).online).toBe(false);
    env.window.dispatchEvent(new Event('online'));
    expect(get(store).online).toBe(true);
    env.window.dispatchEvent(new Event('offline'));
    expect(get(store).online).toBe(false);
  });

  it('detects and activates a waiting service worker update', async () => {
    const env = makeEnvironment({ waiting: true });
    const store = createPwaLifecycleStore(env);
    store.initialize();

    await store.checkForUpdate();

    expect(env.registration.update).toHaveBeenCalledOnce();
    expect(get(store).updateAvailable).toBe(true);
    store.activateUpdate();
    expect(env.worker.postMessage).toHaveBeenCalledWith({ type: 'SKIP_WAITING' });
  });
});
