import { get, writable, type Readable } from 'svelte/store';

export interface PwaLifecycleState {
  online: boolean;
  updateAvailable: boolean;
  checking: boolean;
}

type ServiceWorkerEnvironment = {
  navigator: Navigator;
  window: Window;
};

export function createPwaLifecycleStore(
  environment?: ServiceWorkerEnvironment
): Readable<PwaLifecycleState> & {
  initialize: () => void;
  checkForUpdate: () => Promise<void>;
  activateUpdate: () => void;
} {
  const env =
    environment ??
    (typeof window !== 'undefined' ? { navigator: window.navigator, window } : undefined);
  const { subscribe, update } = writable<PwaLifecycleState>({
    online: env?.navigator.onLine ?? true,
    updateAvailable: false,
    checking: false,
  });

  let initialized = false;
  let registration: ServiceWorkerRegistration | null = null;
  let reloading = false;

  function inspectRegistration(nextRegistration: ServiceWorkerRegistration): void {
    registration = nextRegistration;
    if (nextRegistration.waiting) {
      update((state) => ({ ...state, updateAvailable: true }));
    }

    nextRegistration.addEventListener('updatefound', () => {
      const worker = nextRegistration.installing;
      worker?.addEventListener('statechange', () => {
        if (worker.state === 'installed' && env?.navigator.serviceWorker.controller) {
          update((state) => ({ ...state, updateAvailable: true }));
        }
      });
    });
  }

  function initialize(): void {
    if (!env || initialized) return;
    initialized = true;

    env.window.addEventListener('online', () => {
      update((state) => ({ ...state, online: true }));
    });
    env.window.addEventListener('offline', () => {
      update((state) => ({ ...state, online: false }));
    });

    if ('serviceWorker' in env.navigator) {
      void env.navigator.serviceWorker.ready.then(inspectRegistration);
      env.navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (reloading) return;
        reloading = true;
        env.window.location.reload();
      });
    }
  }

  return {
    subscribe,
    initialize,
    async checkForUpdate() {
      if (!env || !('serviceWorker' in env.navigator)) return;
      update((state) => ({ ...state, checking: true }));
      try {
        registration ??= await env.navigator.serviceWorker.ready;
        await registration.update();
        inspectRegistration(registration);
      } finally {
        update((state) => ({ ...state, checking: false }));
      }
    },
    activateUpdate() {
      const waiting = registration?.waiting;
      if (!waiting || !get({ subscribe }).updateAvailable) return;
      waiting.postMessage({ type: 'SKIP_WAITING' });
    },
  };
}

export const pwaLifecycle = createPwaLifecycleStore();
