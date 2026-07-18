# Push notifications (M11 Sprint 5 / M4.2)

Last updated: 2026-07-18

## Channels

| Channel         | Audience                     | Status                                       |
| --------------- | ---------------------------- | -------------------------------------------- |
| **FCM**         | Play Store / SaaS Android    | M11 Sprint 5 — registration + test send      |
| **UnifiedPush** | Selfhost (NTFY / Gotify / …) | M4.2 — provider enum reserved, no client yet |

Sideload GitHub / Obtainium builds **may omit FCM** (no `google-services.json`)
so a later F-Droid flavor can stay free of proprietary blobs. Those APKs set
`BuildConfig.FCM_ENABLED=false`; the WebView queries the `PushAvailability`
plugin after login and **skips** `PushNotifications.register()`. Calling
`register()` without Firebase init would crash the process (Capacitor Bridge
rethrows on the main thread).

## Neutral copy (DESIGN §2.15)

- Title: `CorrelCore`
- Body: `Time for your daily check-in.`

No streak pressure, no mood/health values in the payload (DSGVO Art. 9).

## API

| Method   | Path                          | Purpose                                       |
| -------- | ----------------------------- | --------------------------------------------- |
| `PUT`    | `/api/v1/devices/push-token`  | Upsert FCM / UnifiedPush token                |
| `DELETE` | `/api/v1/devices/push-token`  | Unregister token                              |
| `GET`    | `/api/v1/devices/push-tokens` | List own registrations (no raw token echo)    |
| `POST`   | `/api/v1/devices/push-test`   | Send check-in reminder to caller’s FCM tokens |

`POST /devices/push-test` returns `503` when `FCM_ENABLED` is false or credentials
are missing (default for selfhost).

See [`docs/API.md`](../API.md) §7c.

## Backend config (SaaS / staging)

```bash
FCM_ENABLED=true
# Prefer one of:
FCM_CREDENTIALS_JSON='{"type":"service_account",...}'
# or
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/fcm-sa.json
```

Install the optional extra on the API image / venv:

```bash
uv sync --extra fcm
# or: pip install 'correlcore-backend[fcm]'
```

## Android / Capacitor

1. Create a Firebase project + Android app `de.correlcore.app`.
2. Download `google-services.json` into `apps/android/android/app/`
   (gitignored — never commit).
3. `pnpm cap:sync` then install the APK.
4. Log in → OS notification permission → token `PUT`s to the API.
5. Call `POST /api/v1/devices/push-test` (Bearer or cookie) to verify delivery.

Without `google-services.json`, Gradle skips the Google Services plugin, sets
`BuildConfig.FCM_ENABLED=false`, and the client never calls `register()`.

Example shape: `apps/android/android/app/google-services.json.example`.

## Client wiring

- `apps/web/src/lib/native/pushNotifications.ts` — Capacitor-only; gates on
  native `PushAvailability.isAvailable()` before permission / register
- `apps/android/.../push/PushAvailabilityPlugin.kt` — exposes `BuildConfig.FCM_ENABLED`
- Triggered from `auth` store after login / hydrate; cleared on logout
- Dependency: `@capacitor/push-notifications@7.0.3`

## Out of scope here

- Scheduled daily reminders / adaptive times (M4.2 product work)
- Weekly digest push delivery (digest payloads already scrubbed; wire later)
- iOS / APNs
- UnifiedPush distributor UX
