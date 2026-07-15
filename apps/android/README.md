# CorrelCore Android (Capacitor)

Native Android shell for the SvelteKit web app ([ADR-0002](../../docs/adr/0002-capacitor-statt-twa.md)).
TWA/Bubblewrap is not used.

## Prerequisites

- Node.js 22+ and pnpm 11+ (monorepo root)
- Android Studio with SDK 34+ (only for device builds — not required for config validation)
- Built web client: `pnpm --filter @correlcore/web build`

The Capacitor `webDir` is `../web/build/client` (SvelteKit `@sveltejs/adapter-node` client output).

## First-time setup

From the repository root:

```bash
pnpm install
pnpm --filter @correlcore/web build
cd apps/android
pnpm exec cap add android   # creates ./android/ (gitignored until committed in M11)
```

## Day-to-day commands

From the repository root:

| Script | Purpose |
| ------ | ------- |
| `pnpm cap:sync` | Copy web build into the Android project and update native deps |
| `pnpm cap:open` | Open the project in Android Studio |
| `pnpm --filter @correlcore/android validate` | CI check — config files only, no SDK |

From `apps/android/`:

```bash
pnpm cap:sync    # same as root cap:sync
pnpm cap:open
pnpm validate
```

## Live reload (optional)

Uncomment `server.url` in `capacitor.config.ts` to point at `http://localhost:5173`
while `pnpm dev` is running, then `pnpm cap:sync`.

## Health Connect (M8/M11)

DSGVO Art. 9 consent is recorded server-side before import (`POST /api/v1/user/me/consents`).
The `@capacitor-community/health-connect` plugin lands in a follow-up M11 sprint.

## CI

`.github/workflows/release-android.yml` validates this scaffold without building an APK.
Full release signing and Play Store upload are tracked in M11.
