import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Capacitor wraps the SvelteKit client bundle (adapter-node output).
 * Build the web app first: `pnpm --filter @correlcore/web build`
 *
 * For live-reload against the Vite dev server, uncomment `server.url`.
 * See apps/android/README.md for the full M11 setup path.
 */
const config: CapacitorConfig = {
  appId: 'de.correlcore.app',
  appName: 'CorrelCore',
  webDir: '../web/build/client',
  android: {
    path: 'android',
  },
  server: {
    // url: 'http://localhost:5173',
    // cleartext: true,
  },
};

export default config;
