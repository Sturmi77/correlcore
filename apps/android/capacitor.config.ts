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
    // REQUIRED for selfhost: WebView origin is https://localhost while the
    // baked API base is often http://<tailnet-ip>:port/api/v1. Chromium
    // blocks that as mixed content unless this is true — cleartext alone
    // is not enough (Tailscale "works in other apps" is expected).
    allowMixedContent: true,
    // Status-bar inset is handled in web CSS (`--page-padding-top` /
    // `safe-area-inset-top`). Keep Capacitor margins disabled to avoid
    // double padding on Android 15 edge-to-edge.
    adjustMarginsForEdgeToEdge: 'disable',
  },
  server: {
    // url: 'http://localhost:5173',
    // Selfhost often uses http://tailnet-ip:port/api/v1 — allow cleartext
    // from the https://localhost WebView (sideload / Obtainium path).
    cleartext: true,
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      // Matches default --color-bg / Claude Design app-icon plate.
      backgroundColor: '#171614',
      showSpinner: false,
    },
    // Present only when google-services.json is present (Play/SaaS builds).
    // Sideload / F-Droid-bound APKs omit the file; JS gates on PushAvailability
    // (BuildConfig.FCM_ENABLED) and must not call register() without it.
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
