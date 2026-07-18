# Android sideload (pre–Play Store)

Last updated: 2026-07-18

Install CorrelCore on Android **without the Play Store**, using a signed APK
from [GitHub Releases](https://github.com/Sturmi77/correlcore/releases).
No GitHub account and no GitHub Mobile app are required for public releases.

M11 context: [`docs/M11_SPRINT_PLAN.md`](../M11_SPRINT_PLAN.md) Sprint 2.
Native shell: [`apps/android/README.md`](../../apps/android/README.md).

## For testers (non-technical)

### Option A — Browser download (simplest)

1. On the phone, open Chrome (or Firefox) and go to:  
   **https://github.com/Sturmi77/correlcore/releases/latest**
2. Under **Assets**, tap `correlcore-<version>.apk`.
3. If Android asks to allow installs from the browser → **Allow**.
4. Open the downloaded file → **Install** → **Open**.

Updates: open the same Releases page again and install the newer APK
(same app id / signing key replaces the old version).

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

| Secret                       | Value                                      |
| ---------------------------- | ------------------------------------------ |
| `ANDROID_KEYSTORE_BASE64`    | contents of `.b64` file (single line)      |
| `ANDROID_KEYSTORE_PASSWORD`  | keystore password                          |
| `ANDROID_KEY_ALIAS`          | e.g. `correlcore`                          |
| `ANDROID_KEY_PASSWORD`       | key password                               |

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
- **workflow_dispatch:** same signed path when secrets exist

Tag example: `git tag v1.1.0 && git push origin v1.1.0`.

## API / selfhost note

Sprint 1–2 shells embed the static SPA. Login against a custom selfhost API
needs the Capacitor Bearer + API base URL work in **Sprint 3**
([ADR-0006](../adr/0006-cookie-auth-mit-capacitor-migration.md)). Until then,
expect limited or broken auth when the WebView cannot use HttpOnly cookies
against a remote API.

## Smoke checklist (sideload APK)

| # | Check                         | Pass? |
| - | ----------------------------- | ----- |
| 1 | Cold start shows CorrelCore UI |       |
| 2 | Navigate to login / register   |       |
| 3 | Offline / network error banner (airplane mode) | |
| 4 | App survives process death (recent apps → reopen) | |
| 5 | Deep link `correlcore://entries/new` opens app   | |
| 6 | Uninstall / reinstall keeps data cleared         | |

Auth success + create entry = Sprint 3 exit criterion.
