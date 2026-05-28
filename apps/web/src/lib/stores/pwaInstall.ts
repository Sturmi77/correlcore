import { get, writable, type Readable } from 'svelte/store';

export const PWA_DISMISSED_STORAGE_KEY = 'cc_pwa_dismissed';

export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
  prompt(): Promise<void>;
}

interface PwaInstallState {
  promptEvent: BeforeInstallPromptEvent | null;
  dismissed: boolean;
  installed: boolean;
}

function readDismissed(): boolean {
  return typeof window !== 'undefined'
    ? localStorage.getItem(PWA_DISMISSED_STORAGE_KEY) === 'true'
    : false;
}

function createPwaInstallStore(): Readable<PwaInstallState> & {
  promptInstall: () => Promise<void>;
  dismiss: () => void;
} {
  const { subscribe, set, update } = writable<PwaInstallState>({
    promptEvent: null,
    dismissed: readDismissed(),
    installed: false,
  });

  if (typeof window !== 'undefined') {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as Navigator & { standalone?: boolean }).standalone === true;

    update((state) => ({ ...state, installed: standalone }));

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      update((state) => ({
        ...state,
        promptEvent: event as BeforeInstallPromptEvent,
        dismissed: readDismissed(),
      }));
    };
    const onInstalled = () => {
      localStorage.setItem(PWA_DISMISSED_STORAGE_KEY, 'true');
      set({ promptEvent: null, dismissed: true, installed: true });
    };

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
    window.addEventListener('appinstalled', onInstalled);
  }

  return {
    subscribe,
    async promptInstall() {
      const promptEvent = get({ subscribe }).promptEvent;
      if (!promptEvent) return;
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice.outcome === 'accepted') {
        localStorage.setItem(PWA_DISMISSED_STORAGE_KEY, 'true');
        update((state) => ({ ...state, dismissed: true, promptEvent: null }));
      }
    },
    dismiss() {
      if (typeof window !== 'undefined') {
        localStorage.setItem(PWA_DISMISSED_STORAGE_KEY, 'true');
      }
      update((state) => ({ ...state, dismissed: true }));
    },
  };
}

export const pwaInstallStore = createPwaInstallStore();
