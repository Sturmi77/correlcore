# CorrelCore Android (Capacitor)

Native Android shell for the SvelteKit web app ([ADR-0002](../../docs/adr/0002-capacitor-statt-twa.md)).
TWA/Bubblewrap is not used.

**Milestone:** M11 Sprints 1–5 complete (Play Console exit open — [#429](https://github.com/Sturmi77/correlcore/issues/429)). Plan: [`docs/M11_SPRINT_PLAN.md`](../../docs/M11_SPRINT_PLAN.md).

## Prerequisites

- Node.js 22+ and pnpm 11+ (monorepo root)
- JDK 21
- Android Studio **or** Android SDK 36 + build-tools (only for device/APK builds)
- Python 3 + Pillow (optional — regenerate launcher/splash from `apps/web/static/icons/`)

The Capacitor `webDir` is `../web/build-capacitor` — a static SPA produced with
`CAPACITOR_BUILD=1` / `pnpm --filter @correlcore/web build:capacitor`
(`@sveltejs/adapter-static` fallback). Production web hosting still uses
`adapter-node` via the normal `pnpm build`.

## App identity

| Field           | Value                      |
| --------------- | -------------------------- |
| `applicationId` | `de.correlcore.app`        |
| `appName`       | CorrelCore                 |
| Deep link       | `correlcore://entries/new` |

## First-time setup

From the repository root:

```bash
pnpm install
pnpm cap:sync          # build:capacitor + cap sync android
pnpm cap:open          # opens Android Studio
```

USB debug install from Android Studio: Run ▶ on a device/emulator (API 31+ recommended; `minSdk` 24).

CLI debug APK (SDK required):

```bash
pnpm cap:assemble:debug
# → apps/android/android/app/build/outputs/apk/debug/app-debug.apk
```

## Day-to-day commands

| Script                                           | Purpose                                              |
| ------------------------------------------------ | ---------------------------------------------------- |
| `pnpm cap:sync`                                  | Capacitor SPA build + copy into Android project      |
| `pnpm cap:open`                                  | Open the project in Android Studio                   |
| `pnpm cap:assemble:debug`                        | Sync + `./gradlew assembleDebug`                     |
| `pnpm --filter @correlcore/android validate`     | CI check — config files only, no SDK                 |
| `pnpm --filter @correlcore/android assets:brand` | Regenerate launcher/splash PNGs from web brand icons |

## Live reload (optional)

Uncomment `server.url` in `capacitor.config.ts` to point at `http://localhost:5173`
(use `10.0.2.2` for the Android emulator), then `pnpm cap:sync` while `pnpm dev` runs.

## Push (Sprint 5)

FCM is **optional**. Place a real `google-services.json` under `android/app/` for
Play/SaaS builds; omit it for GitHub sideload / future F-Droid flavors.
Gradle sets `BuildConfig.FCM_ENABLED` from that file; the WebView asks
`PushAvailability` before calling `PushNotifications.register()` so sideload
APKs do not crash after login.
See [`docs/features/PUSH.md`](../../docs/features/PUSH.md).

## Error tracking (optional)

Bake GlitchTip into Capacitor builds by setting `PUBLIC_GLITCHTIP_DSN` (and
optionally `PUBLIC_GLITCHTIP_ENVIRONMENT`) at `pnpm cap:sync` / CI time. The
release workflow reads `secrets.PUBLIC_GLITCHTIP_DSN` or `secrets.GLITCHTIP_DSN`.

## Backup / data extraction

`AndroidManifest` sets `android:allowBackup="false"` so system backup / device
transfer does not copy WebView IndexedDB offline entries (mood, notes,
symptoms). Revisit only with an explicit `dataExtractionRules` policy.

## Homescreen widget (Sprint 4)

Jetpack Glance widget + WorkManager (15 min). Docs: [`docs/features/WIDGET.md`](../../docs/features/WIDGET.md).

After login in the Capacitor app, add the **CorrelCore check-in** widget from the
launcher widget picker. “+ Add entry” uses `correlcore://entries/new`.

## Health Connect (M8/M11)

DSGVO Art. 9 consent is recorded server-side before import (`POST /api/v1/user/me/consents`).
The `@capacitor-community/health-connect` plugin lands in a follow-up M11 sprint.

## Release signing (Sprint 2)

Sideload / GitHub Releases path: [`docs/selfhost/ANDROID_SIDELOAD.md`](../../docs/selfhost/ANDROID_SIDELOAD.md).

```bash
export ANDROID_KEYSTORE_PATH=/path/to/correlcore-upload.keystore
export ANDROID_KEYSTORE_PASSWORD=...
export ANDROID_KEY_ALIAS=correlcore
export ANDROID_KEY_PASSWORD=...
pnpm cap:assemble:release
```

CI secrets: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`,
`ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. On `v*` tags the workflow attaches
signed APK + AAB + `SHA256SUMS.txt` to the GitHub Release.

## CI

[`.github/workflows/release-android.yml`](../../.github/workflows/release-android.yml):

1. Validates Capacitor config (no SDK)
2. Builds debug APK (`assembleDebug`) on PRs / main
3. Builds **signed** release APK/AAB on `v*` tags / `workflow_dispatch` when
   signing secrets are configured
