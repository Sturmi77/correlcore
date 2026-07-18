# Android sideload (pre–Play Store)

Last updated: 2026-07-18

Install CorrelCore on Android **without the Play Store**, using a signed APK
from [GitHub Releases](https://github.com/Sturmi77/correlcore/releases).
No GitHub account and no GitHub Mobile app are required for public releases.

M11 context: [`docs/M11_SPRINT_PLAN.md`](../M11_SPRINT_PLAN.md) Sprint 2.
Ops checklist (signing secrets / Play): [`M11_OPS_CHECKLIST.md`](M11_OPS_CHECKLIST.md)
([GitHub #429](https://github.com/Sturmi77/correlcore/issues/429)).
Native shell: [`apps/android/README.md`](../../apps/android/README.md).

## For testers (non-technical)

### Option A — Browser download (simplest)

1. On the phone, open Chrome (or Firefox) and go to:  
   **https://github.com/Sturmi77/correlcore/releases/latest**
2. At the **top of the release notes**, tap **Download APK**  
   (`correlcore-<version>.apk`).  
   (GitHub’s **Assets** list is easy to miss on mobile — the note link is the
   intended path.)
3. If Android asks to allow installs from the browser → **Allow**.
4. Open the downloaded file → **Install** → **Open**.

Updates: open the same Releases page again and install the newer APK
(same app id / signing key replaces the old version).

> **v1.0.0 note:** The first public tag was a selfhost/Docker release and does
> **not** include an Android APK. Use a later `v*` release once signing secrets
> are configured and `Release — Android` has attached `correlcore-*.apk`.

### Option B — Obtainium (auto-updates)

1. Install [Obtainium](https://obtainium.imranr.dev/) (F-Droid or its APK).
2. Add app → source **GitHub** → repo  
   `https://github.com/Sturmi77/correlcore`
3. Prefer release assets matching `correlcore-*.apk`.
4. Obtainium notifies you when a new release APK is available.

### Optional checksum check

Each release includes `SHA256SUMS.txt`. On a computer:

```bash
sha256sum -c SHA256SUMS.txt
```

On Android, apps such as “Hash Checker” can verify the APK digest against the
file on the Release page.

## Maintainer: publish a signed APK

### One-time: create upload keystore + GitHub Secrets

```bash
keytool -genkeypair -v \
  -keystore correlcore-upload.keystore \
  -alias correlcore \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass 'USE-A-LONG-SECRET' \
  -keypass 'USE-A-LONG-SECRET' \
  -dname 'CN=CorrelCore, OU=Mobile, O=CorrelCore, L=Unknown, ST=Unknown, C=AT'

base64 -w0 correlcore-upload.keystore > correlcore-upload.keystore.b64
```

Add repository secrets (Settings → Secrets and variables → Actions):

| Secret                      | Value                                 |
| --------------------------- | ------------------------------------- |
| `ANDROID_KEYSTORE_BASE64`   | contents of `.b64` file (single line) |
| `ANDROID_KEYSTORE_PASSWORD` | keystore password                     |
| `ANDROID_KEY_ALIAS`         | e.g. `correlcore`                     |
| `ANDROID_KEY_PASSWORD`      | key password                          |

Store the `.keystore` offline encrypted; losing it blocks updates for
sideload users (and complicates Play App Signing later).

### Local signed build

```bash
export ANDROID_KEYSTORE_PATH=/absolute/path/to/correlcore-upload.keystore
export ANDROID_KEYSTORE_PASSWORD=...
export ANDROID_KEY_ALIAS=correlcore
export ANDROID_KEY_PASSWORD=...
export ANDROID_VERSION_NAME=1.0.0-android.1
export ANDROID_VERSION_CODE=2
pnpm cap:assemble:release
# → apps/android/android/app/build/outputs/apk/release/app-release.apk
# → apps/android/android/app/build/outputs/bundle/release/app-release.aab
```

Or use `apps/android/android/keystore.properties` from
[`apps/android/keystore.properties.example`](../../apps/android/keystore.properties.example).

### CI

[`.github/workflows/release-android.yml`](../../.github/workflows/release-android.yml):

- **PRs / main pushes:** debug APK artifact (unsigned debug key)
- **`v*` tags** (and secrets set): signed `assembleRelease` + `bundleRelease`,
  upload artifact + attach `correlcore-<ver>.apk`, `.aab`, and `SHA256SUMS.txt`
  to the GitHub Release
- **workflow_dispatch:** signed build; optional input `attach_to_tag` (e.g. `v1.0.1`)
  re-attaches APK/AAB to an existing GitHub Release if a tag push missed them

Tag example: `git tag v1.1.0 && git push origin v1.1.0`.

If the release notes show **Download APK** but the link is **404**, no asset was
attached — re-run **Actions → Release - Android (Capacitor) → Run workflow** with
`attach_to_tag=vX.Y.Z` (after signing secrets are set).

## API / selfhost note

Capacitor builds use Bearer auth (ADR-0006) when built with `VITE_CAPACITOR=1`.
Signed GitHub Release APKs **must** bake an absolute API URL — relative `/api/v1`
resolves to `https://localhost/api/v1` in the WebView and login fails with a
network error.

Set the URL at build time:

```bash
VITE_API_BASE_URL=https://your-host.example/api/v1 pnpm cap:sync
```

CI (`release-android.yml` signed job) requires repository secret/variable
`VITE_API_BASE_URL` (or `workflow_dispatch` input `vite_api_base_url`) and fails
the build if the value is missing or relative.

Selfhost testers can also set the API base **before sign-in** on Login/Register
(„API server“), or later under **Settings → App & offline** (runtime override,
localStorage — not a secret). Sign in again after changing servers.

The API always allows the Capacitor WebView origin `https://localhost`
(see `settings.cors_allow_origins`). Still list your browser/PWA web origin
in `CORS_ORIGINS`. Selfhost HTTP API bases (`http://…/api/v1`) are permitted
by the sideload APK (`usesCleartextTraffic` / Capacitor `cleartext`).

**Push / FCM:** GitHub Release APKs typically ship **without** `google-services.json`,
so Firebase push stays off. That is intentional for Obtainium / future F-Droid.
Play/SaaS builds can include FCM — see [`docs/features/PUSH.md`](../features/PUSH.md).

## Smoke checklist (sideload APK)

| #   | Check                                             | Pass? |
| --- | ------------------------------------------------- | ----- |
| 1   | Cold start shows CorrelCore UI                    |       |
| 2   | Navigate to login / register                      |       |
| 3   | Offline / network error banner (airplane mode)    |       |
| 4   | App survives process death (recent apps → reopen) |       |
| 5   | Deep link `correlcore://entries/new` opens app    |       |
| 6   | Uninstall / reinstall keeps data cleared          |       |

Auth success + create entry = Sprint 3 exit criterion.
