# PWA Hardening

Last updated: 2026-06-30

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

## Offline-First Sync (M4.1)

Full Dexie-backed offline sync is implemented behind a feature flag for
verified users. See [ADR-0036](../adr/0036-offline-sync-v1-scope.md) and
[`M4.1_SPRINT_PLAN.md`](../M4.1_SPRINT_PLAN.md).

| Component         | Location                                                                      |
| ----------------- | ----------------------------------------------------------------------------- |
| Local DB          | `apps/web/src/lib/offline/db.ts` — IndexedDB via Dexie (`correlcore-offline`) |
| Change outbox     | `change_log` table — append-only, monotone `seq`                              |
| Sync orchestrator | `syncOrchestrator.ts` — push on reconnect / visibility                        |
| API               | `POST /api/v1/sync/push`, `GET /api/v1/sync/pull`                             |
| Conflict history  | `GET /api/v1/user/sync-conflicts` (90-day retention)                          |

**Enable for testing**

- Settings → App & offline → “Enable offline sync”, or
- `localStorage.setItem('cc_offline_sync_enabled', 'true')`, or
- Build-time `VITE_OFFLINE_SYNC_ENABLED=true`

**Default:** off — online autosave (ADR-0013) remains the default path.

**Privacy:** push/pull payloads may contain Art. 9 health data; conflict log
rows redact plaintext notes. Background upload runs only after explicit user
sync (reconnect, visibility, or “Sync now”) — not silently.

## Manifest and iOS Meta

The manifest uses:

- `display: standalone`
- `start_url: /`
- `theme_color: #6356d9`
- maskable SVG app icon at `/icons/icon.svg`

`app.html` includes iOS standalone meta tags and an `apple-touch-icon` link.

## Roadmap Note

Glance homescreen widget shipped in **M11 Sprint 4** — see [`WIDGET.md`](WIDGET.md).
UnifiedPush and app lock remain **M4.2**. FCM is optional for Capacitor builds
(**M11 Sprint 5** registration code; live Firebase/Play verification open #429).
