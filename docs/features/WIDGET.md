# Android Homescreen Widget (M11)

Last updated: 2026-07-18

Jetpack Glance widget for CorrelCore Android (`de.correlcore.app`). Complements
the M4 PWA install prompt with a true launcher widget.

## What it shows

| Element           | Source                                                                 |
| ----------------- | ---------------------------------------------------------------------- |
| Brand             | Static “CorrelCore” label                                              |
| Headline          | “No entry yet” when `has_entry` is false; otherwise 7-day mood average |
| “+ Add entry”     | Deep link `correlcore://entries/new` → entry sheet                     |
| Updated timestamp | Last successful WorkManager sync                                       |

Sizes: resizable from ~4×1; verify 4×1 and 4×2 on Android 12/14 (light/dark).

## API

```
GET /api/v1/widget/summary
Authorization: Bearer <access_token>
```

Response (≤1 KB): `has_entry`, `mood_avg_7d`, `suggested_next_entry_at`.
See [`docs/API.md`](../API.md) §7b.

## Sync

- **WorkManager** unique periodic work every **15 minutes**, constraints:
  - network connected
  - battery not low
- Immediate refresh when the user logs in/out (Capacitor plugin) or first
  places the widget on the home screen.

## Auth bridge (ADR-0006 exception)

Capacitor keeps JWTs **in memory** for the WebView (ADR-0006). The Glance
process cannot read that heap, so login/refresh/logout also mirrors the
**access token**, **refresh token**, and **API base** into an app-private
SharedPreferences file (`correlcore_widget`) via the Capacitor plugin
`WidgetCredentials`.

- Cleared on logout and when refresh + summary both fail (401/403).
- On 401 from `GET /widget/summary`, WorkManager rotates via
  `SessionRefreshCoordinator` (in-process lock shared with the WebView’s
  `SecureSession.refresh`). Refresh tokens are single-use; without this
  lock a widget rotate followed by a stale WebView refresh triggers API
  `revoke_all` and the app “loses contact” after the ~15 minute access TTL.
- The coordinator dual-writes rotated access + refresh to
  `WidgetCredentialsStore` **and** `SecureSessionStore`.
- Browser / cookie builds never call the plugin.
- Never write these tokens to web `localStorage` (ADR-0006).

Web helpers: `apps/web/src/lib/api/widgetCredentials.ts` (invoked from
`sessionTokens` / `apiBase`).

## Native layout

| File                                     | Role                             |
| ---------------------------------------- | -------------------------------- |
| `…/widget/CorrelCoreWidget.kt`           | Glance UI + receiver             |
| `…/widget/WidgetRefreshWorker.kt`        | HTTP poll + WorkManager          |
| `…/widget/WidgetCredentialsPlugin.kt`    | Capacitor bridge                 |
| `…/widget/WidgetCredentialsStore.kt`     | SharedPreferences                |
| `…/session/SessionRefreshCoordinator.kt` | Shared refresh lock + dual-write |
| `res/xml/correlcore_widget_info.xml`     | AppWidget metadata               |

## Manual QA checklist

- [ ] Android 12 emulator — light + dark, 4×1 and 4×2
- [ ] Android 14 device/emulator — light + dark, 4×1 and 4×2
- [ ] Signed-out state shows “Sign in to see mood”
- [ ] After login, widget updates within one WorkManager run
- [ ] Leave app backgrounded >15 minutes → widget still refreshes (refresh rotate)
- [ ] “+ Add entry” opens the Capacitor app on the new-entry sheet
- [ ] Airplane mode → status degrades gracefully; reconnect recovers
- [ ] Logout → widget shows signed-out and stops polling with credentials

## Permissions

Only `INTERNET` (already required by the Capacitor shell). No location or
notification permission for the widget itself.

## Out of scope (later sprints)

- FCM / UnifiedPush (Sprint 5)
- iOS widgets
- Play Store listing screenshots (Sprint 6)
