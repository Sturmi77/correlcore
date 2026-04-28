import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export type Theme = 'light' | 'dark';

function createThemeStore() {
  // NOTE: localStorage unavailable in sandboxed iframes — use in-memory fallback
  const getInitial = (): Theme => {
    if (!browser) return 'dark';
    // Read from data-theme attribute first (SSR compat)
    const attr = document.documentElement.getAttribute('data-theme');
    if (attr === 'light' || attr === 'dark') return attr;
    // Fall back to system preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const { subscribe, set, update } = writable<Theme>(getInitial());

  return {
    subscribe,
    toggle() {
      update((current) => {
        const next: Theme = current === 'dark' ? 'light' : 'dark';
        if (browser) {
          document.documentElement.setAttribute('data-theme', next);
          // Persist in localStorage only when available (not sandboxed)
          try {
            localStorage.setItem('moodsync-theme', next);
          } catch {
            // Silently ignore — sandboxed environment
          }
        }
        return next;
      });
    },
    set(theme: Theme) {
      if (browser) {
        document.documentElement.setAttribute('data-theme', theme);
        try {
          localStorage.setItem('moodsync-theme', theme);
        } catch {
          // Silently ignore
        }
      }
      set(theme);
    },
  };
}

export const theme = createThemeStore();
