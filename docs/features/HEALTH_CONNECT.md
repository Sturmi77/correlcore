# Health Connect (Android)

Last updated: 2026-08-02 · Milestone: **M8 Sprint 3–4** (#172) · Strategy: [ADR-0042](../adr/0042-health-connect-bridge-strategy.md)

CorrelCore reads a minimal set of on-device health data from **Health Connect**
on Android. This document lists every permission, the data flow, and the manual
device QA required (the native path is not built in CI without an Android SDK).

## Scope

- **Sprint 3** — the bridge: availability, permission request, and raw reads of
  sleep + heart rate exposed to the WebView.
- **Sprint 4** — sleep import: `POST /api/v1/health-connect/import` fills
  `sleep_minutes` on existing entries (manual wins), a per-field toggle, and the
  in-app foreground "Sync now" action.

Still out of scope: **heart-rate persistence** (no entry column yet — HR is read
at the permission level but not stored), **native WorkManager background sync**
(foreground sync only for now), cycle/menstruation import (separate
sub-milestone), and the Play Store data-safety declaration (Play exit).

## Sprint 4 — import

`POST /api/v1/health-connect/import` — body `{ sleep: [{ entry_date, sleep_minutes }] }`.

- **Consent-gated:** 403 unless the Art. 9 consent (`consent_log`) is granted.
- **Per-field toggle:** `user_preferences.health_connect_sync_sleep_enabled`
  (default true); when off, the endpoint imports nothing.
- **Manual wins:** only entries whose `sleep_minutes` is NULL are filled; a typed
  value is never overwritten.
- **No fabricated entries:** days without a logged entry are skipped, because
  `mood`/`energy`/`stress` are required and must not be invented.

The web hub (`/health-connect`) reads HC sleep via the bridge, aggregates
sessions into one `sleep_minutes` per wake-date (`lib/native/healthConnectSync.ts`),
and calls the import endpoint.

## Permissions (data minimization)

Declared in `apps/android/android/app/src/main/AndroidManifest.xml`:

| Permission                                  | Purpose                                     |
| ------------------------------------------- | ------------------------------------------- |
| `android.permission.health.READ_SLEEP`      | Read `SleepSessionRecord` (duration/timing) |
| `android.permission.health.READ_HEART_RATE` | Read `HeartRateRecord` (samples)            |

**No** movement, steps, location, or other health permissions are requested. The
read permission set is hard-coded in `HealthConnectPlugin.permissions` (Kotlin),
so the WebView cannot widen it.

## Consent gate (DSGVO Art. 9)

Every read is gated twice:

1. **Server-side consent** (`consent_log`, Issue #31) — `canUseHealthConnectImport()`
   must return true before the TS bridge will call the native plugin.
2. **Health Connect permission** — the OS permission sheet, requested natively.

The rationale/consent screen lives at the web route **`/health-connect`**
(`apps/web/src/routes/health-connect/+page.svelte`). Health Connect launches it
via the manifest rationale intent-filters (`ACTION_SHOW_PERMISSIONS_RATIONALE`
and the Android 14+ `VIEW_PERMISSION_USAGE` / `HEALTH_PERMISSIONS` activity-alias),
routed by `MainActivity`.

## Data flow

```
Health Connect (on device)
   → HealthConnectPlugin.kt (read sleep + HR, sleep+HR only)
   → window.Capacitor.Plugins.HealthConnect
   → lib/native/healthConnect.ts (consent-gated)
   → [Sprint 4] backend import → entries.source = wearable (manual wins)
```

No third-party cloud is involved; data moves from Health Connect into the user's
own CorrelCore instance.

## Native plugin API (`HealthConnect`)

| Method                                  | Result                                                              |
| --------------------------------------- | ------------------------------------------------------------------- |
| `isAvailable()`                         | `{ available, status }` — Health Connect SDK status on the device   |
| `checkPermissions()`                    | `{ granted, available }` for the fixed sleep + HR set               |
| `requestPermissions()`                  | Launches the HC permission sheet; resolves with the new grant state |
| `readSleepAndHeartRate({ start, end })` | `{ sleep[], heartRate[] }` for the ISO-8601 range                   |

## Build & verify (manual — no CI SDK build)

Config-only CI check (no SDK):

```bash
pnpm --filter @correlcore/android validate
```

Full device build (needs JDK 21 + Android SDK 36):

```bash
pnpm cap:sync
pnpm cap:assemble:debug   # apps/android/android/app/build/outputs/apk/debug/app-debug.apk
```

### Device QA checklist

- [ ] Install the **sideload** debug/release APK on a device with Health Connect (Android 14 built-in; Android 13 install the HC app).
- [ ] Without server consent granted: `/health-connect` shows "grant consent first" and no permission sheet appears.
- [ ] After granting server consent: "Grant Health Connect access" opens the OS permission sheet listing **only** Sleep + Heart rate.
- [ ] Deny → `checkPermissions()` stays `granted: false`; Allow → `granted: true`.
- [ ] `readSleepAndHeartRate` returns records for a range that has data; empty arrays otherwise.
- [ ] Health Connect app → "See app permissions" launches the rationale page.
- [ ] Hardened ROMs (e.g. GrapheneOS): confirm the permission sheet launches from the sideload APK (known edge case).

## Notes

- Health Connect client version is pinned in `apps/android/android/variables.gradle`
  (`healthConnectVersion`); bump alongside HC client updates.
- The Play Store **health apps declaration** is required only for Play distribution
  and is handled at the Play exit, not here.
