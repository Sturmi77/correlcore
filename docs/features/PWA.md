# PWA Hardening

Last updated: 2026-05-28

## Install Flow

The web app listens for `beforeinstallprompt` in `pwaInstallStore`. When the
browser exposes an install prompt and the user has not dismissed it, Home shows
a compact install banner.

- Dismissal is stored in `localStorage` as `cc_pwa_dismissed`.
- Accepted installs also mark the banner dismissed.
- iOS Safari does not expose `beforeinstallprompt`; installation remains the
  native Share Sheet flow.

## Offline Behavior

`src/service-worker.ts` caches only the SvelteKit app shell and static assets.
Navigation failures fall back to `/offline`.

The service worker explicitly skips `/api/*`, so authenticated API responses,
health data, entries, tags, and insights are not cached by the browser Cache
API.

M4 does not implement offline entry creation or background sync. Full Dexie
offline-first sync, sync conflict logs, and push/pull endpoints remain follow-up
scope after M4.

## Manifest and iOS Meta

The manifest uses:

- `display: standalone`
- `start_url: /`
- `theme_color: #6356d9`
- maskable SVG app icon at `/icons/icon.svg`

`app.html` includes iOS standalone meta tags and an `apple-touch-icon` link.

## Roadmap Note

Native Android widgets are not part of M4. The current roadmap keeps them in a
later Android path via TWA/Glance once the PWA baseline and Play Store strategy
are settled.
