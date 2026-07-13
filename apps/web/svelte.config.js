import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    alias: {
      $lib: './src/lib',
      $i18n: './src/lib/i18n',
    },
    // Absolute Asset-Pfade erzwingen.
    // Default seit Kit 2.x ist `relative: true` — das bricht alle nicht-Root-
    // Routes im SPA-Mode (ssr=false), weil der gerenderte HTML-Index für
    // /auth/login mit `../_app/...`-Pfaden zu `/auth/_app/...` aufgelöst wird
    // (404). Mit absoluten Pfaden (`/_app/...`) funktioniert jede Route.
    paths: {
      relative: false,
    },
    serviceWorker: {
      register: false,
    },
  },
};

export default config;
