# CorrelCore Android (Capacitor)

Native Android shell for the SvelteKit web app ([ADR-0002](../../docs/adr/0002-capacitor-statt-twa.md)).
TWA/Bubblewrap is not used.

**Milestone:** M11 Sprint 1 (production shell). Plan: [`docs/M11_SPRINT_PLAN.md`](../../docs/M11_SPRINT_PLAN.md).

## Prerequisites

- Node.js 22+ and pnpm 11+ (monorepo root)
- JDK 21
- Android Studio **or** Android SDK 35 + build-tools (only for device/APK builds)
- Python 3 + Pillow (optional — only to regenerate brand icons/splash)

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

USB debug install from Android Studio: Run ▶ on a device/emulator (API 31+ recommended; `minSdk` 23).

CLI debug APK (SDK required):

```bash
pnpm cap:assemble:debug
# → apps/android/android/app/build/outputs/apk/debug/app-debug.apk
```

## Day-to-day commands

| Script                                           | Purpose                                            |
| ------------------------------------------------ | -------------------------------------------------- |
| `pnpm cap:sync`                                  | Capacitor SPA build + copy into Android project    |
| `pnpm cap:open`                                  | Open the project in Android Studio                 |
| `pnpm cap:assemble:debug`                        | Sync + `./gradlew assembleDebug`                   |
| `pnpm --filter @correlcore/android validate`     | CI check — config files only, no SDK               |
| `pnpm --filter @correlcore/android assets:brand` | Regenerate launcher/splash PNGs from brand palette |

## Live reload (optional)

Uncomment `server.url` in `capacitor.config.ts` to point at `http://localhost:5173`
(use `10.0.2.2` for the Android emulator), then `pnpm cap:sync` while `pnpm dev` runs.

## Health Connect (M8/M11)

DSGVO Art. 9 consent is recorded server-side before import (`POST /api/v1/user/me/consents`).
The `@capacitor-community/health-connect` plugin lands in a follow-up M11 sprint.

## CI

[`.github/workflows/release-android.yml`](../../.github/workflows/release-android.yml):

1. Validates Capacitor config (no SDK)
2. Builds debug APK via JDK 21 + Android SDK (`assembleDebug`) and uploads the artifact

Release signing and Play Store upload are Sprint 2+.
