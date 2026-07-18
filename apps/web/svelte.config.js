import nodeAdapter from '@sveltejs/adapter-node';
import staticAdapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/**
 * Production web (Docker / selfhost) uses adapter-node.
 * Capacitor Android shell needs a static SPA fallback (index.html) — set
 * CAPACITOR_BUILD=1 when building for `pnpm cap:sync`.
 */
const isCapacitorBuild = process.env.CAPACITOR_BUILD === '1';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: isCapacitorBuild
      ? staticAdapter({
          pages: 'build-capacitor',
          assets: 'build-capacitor',
          fallback: 'index.html',
          precompress: false,
          strict: false,
        })
      : nodeAdapter(),
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
