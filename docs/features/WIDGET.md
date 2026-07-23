# Android Homescreen Widget (M11)

Last updated: 2026-07-18

Jetpack Glance widget for CorrelCore Android (`de.correlcore.app`). Complements
the M4 PWA install prompt with a true launcher widget.

## What it shows

| Element           | Source                                                                 |
| ----------------- | ---------------------------------------------------------------------- |
| Brand             | Static “CorrelCore” label                                              |
| Headline          | “No entry yet” when `has_entry` is false; otherwise 7-day mood average |
| “+ Add entry”     | Deep link `correlcore://entries/new` → entry sheet (see below)         |
| Updated timestamp | Last successful WorkManager sync                                       |

Sizes: resizable from ~4×1; verify 4×1 and 4×2 on Android 12/14 (light/dark).

## Deep link

`correlcore://entries/new` is declared in `AndroidManifest.xml` and routed into
the WebView by [`deepLinks.ts`](../../apps/web/src/lib/native/deepLinks.ts) via
`@capacitor/app`:

- **Cold start** — the launch intent is consumed before the WebView boots, so it
  is read with `App.getLaunchUrl()`.
- **Warm start** — `MainActivity` is `singleTask`, so Android delivers
  `onNewIntent`, surfaced as the `appUrlOpen` event.

Both map to `/?openEntry=1`, the same path the in-app “+” button uses, so the
widget and the app open an identical sheet. An optional `?date=YYYY-MM-DD`
pre-selects the entry date; malformed values are dropped. Unknown
`correlcore://` targets are ignored rather than navigated to.

If the user is signed out, the link is routed through
`/auth/login?next=/?openEntry=1` and the sheet opens after login. This is
explicit rather than automatic: `/` is a public route, so the layout's anonymous
guard — which is what normally preserves the target in `next` — never fires for
the landing page.

## API

```
GET /api/v1/widget/summary?tz=America/Los_Angeles
Authorization: Bearer <access_token>
```

Response (≤1 KB): `has_entry`, `mood_avg_7d`, `suggested_next_entry_at`.
See [`docs/API.md`](../API.md) §7b.

### `tz` — device timezone

Entries are stored against a device-local `entry_date` (`localIsoDate`), so
resolving “today” from UTC made the widget disagree with the app for anyone
whose local day differs from UTC: `has_entry` false and a shifted 7-day window
despite today’s entry existing (#445).

The worker sends `ZoneId.systemDefault().id` on every poll, and the server
resolves the local day, the 7-day mood window and the suggested-entry hour in
that zone. `suggested_next_entry_at` stays UTC on the wire but now keeps its
intended local wall-clock hour across DST transitions.

Omitted or unknown zone names fall back to UTC rather than failing the request —
a widget must not break because a device reports a zone this server’s tzdata
does not know.

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
- [ ] “+ Add entry” opens the new-entry sheet from a **cold** start (app killed)
- [ ] “+ Add entry” opens the new-entry sheet from a **warm** start (app backgrounded)
- [ ] “+ Add entry” while signed out → sheet opens after login completes
- [ ] Airplane mode → status degrades gracefully; reconnect recovers
- [ ] Logout → widget shows signed-out and stops polling with credentials

## Permissions

Only `INTERNET` (already required by the Capacitor shell). No location or
notification permission for the widget itself.

## Out of scope (later sprints)

- FCM / UnifiedPush (Sprint 5)
- iOS widgets
- Play Store listing screenshots (Sprint 6)
