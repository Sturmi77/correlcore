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
  // Static SPA output from `pnpm --filter @correlcore/web build:capacitor`
  webDir: '../web/build-capacitor',
  android: {
    path: 'android',
    allowMixedContent: false,
  },
  server: {
    // url: 'http://localhost:5173',
    // cleartext: true,
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#7c6af5',
      showSpinner: false,
    },
  },
};

export default config;
