# Android sideload (pre–Play Store)

Last updated: 2026-07-19

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
> **not** include an Android APK. Signed sideload APKs are available from **`v1.0.1`**
> onward; prefer the latest **`v1.x`** release (e.g. **`v1.6.0`**).

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
export ANDROID_VERSION_NAME=1.3.0
export ANDROID_VERSION_CODE=1003000
pnpm cap:assemble:release   # builds both flavors
# sideload APK (Health Connect, this sideload channel):
# → apps/android/android/app/build/outputs/apk/sideload/release/app-sideload-release.apk
# play AAB (HC-free, Play Console upload):
# → apps/android/android/app/build/outputs/bundle/playRelease/app-play-release.aab
```

**Flavors:** the signed **sideload APK** (with Health Connect) is what ships on
GitHub Releases / Obtainium; the **play AAB** is HC-free for the Play Store
(AP-HC Option A — [`../M11_PLAY_STORE_GAP_ANALYSIS.md`](../M11_PLAY_STORE_GAP_ANALYSIS.md) §4).
The Release keeps the stable asset names `correlcore-<ver>.apk` (sideload) and
`correlcore-<ver>.aab` (play).

Or use `apps/android/android/keystore.properties` from
[`apps/android/keystore.properties.example`](../../apps/android/keystore.properties.example).

**CI version encoding:** on `v*` tags, [`release-android.yml`](../../.github/workflows/release-android.yml)
strips the leading `v` for `versionName` (e.g. `v1.5.0` → `1.5.0`) and sets
`versionCode = major×1_000_000 + minor×1_000 + patch` (e.g. `1.3.0` → `1003000`).
Manual `workflow_dispatch` without a tag falls back to `1.0.0-android.<run>` / run number.

### CI

[`.github/workflows/release-android.yml`](../../.github/workflows/release-android.yml):

- **PRs / main pushes:** debug APK artifact for both flavors (unsigned debug key; sideload APK uploaded)
- **`v*` tags** (and secrets set): signed `assembleSideloadRelease` + `bundlePlayRelease`,
  HC flavor-split asserted, then attach `correlcore-<ver>.apk` (sideload),
  `.aab` (play), and `SHA256SUMS.txt` to the GitHub Release
- **workflow_dispatch:** signed build; optional input `attach_to_tag` (e.g. `v1.0.1`)
  re-attaches APK/AAB to an existing GitHub Release if a tag push missed them.
  The build is checked out **from that tag**, so backfilled binaries always match
  the release they are attached to.

Tag example: `git tag v1.5.0 && git push origin v1.5.0`.

The **Download APK** block is written only by the Android workflow, and only
after it has verified the APK is attached to the release. A tag built without
signing secrets therefore has **no** download block at all rather than a 404
link. If a release is missing the block, re-run **Actions → Release - Android
(Capacitor) → Run workflow** with `attach_to_tag=vX.Y.Z` (after signing secrets
are set).

## API / selfhost note

Capacitor builds use Bearer auth (ADR-0006) when built with `VITE_CAPACITOR=1`.
Signed GitHub Release APKs **must** bake an absolute API URL — relative `/api/v1`
resolves to `https://localhost/api/v1` in the WebView and login fails with a
network error.

### Persistent session QA (Issue #453)

With **„Angemeldet bleiben“** checked (default):

1. Sign in → force-stop the app → reopen → still authenticated (no login form).
2. Sign out → reopen → login form; no stale session.
3. Uncheck **„Angemeldet bleiben“** → sign in → force-stop → reopen → login required.

Refresh tokens are stored in Android EncryptedSharedPreferences (Keystore), not
in WebView `localStorage`. See [`docs/features/PERSISTENT_SESSION_PLAN.md`](../features/PERSISTENT_SESSION_PLAN.md).

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
in `CORS_ORIGINS`.

**Root cause for “Tailscale works but APK login fails” (fixed ≥ v1.0.4):** the
WebView document is `https://localhost` while sideload builds often bake an
`http://<tailnet-ip>:…/api/v1` base. Chromium blocks that as **mixed content**
unless `android.allowMixedContent: true` (in addition to
`usesCleartextTraffic` / `server.cleartext`). Native Tailscale apps are
unaffected because they are not an HTTPS WebView page.

**Push / FCM:** GitHub Release APKs typically ship **without** `google-services.json`,
so Firebase push stays off (`BuildConfig.FCM_ENABLED=false`; no
`PushNotifications.register()`). That is intentional for Obtainium / future
F-Droid. Play/SaaS builds can include FCM — see
[`docs/features/PUSH.md`](../features/PUSH.md).

**Error tracking (optional):** set repository secret `PUBLIC_GLITCHTIP_DSN`
(or reuse `GLITCHTIP_DSN`) so the Capacitor SPA build bakes GlitchTip into the
APK. Without it, client error tracking stays off (zero outbound).

## Smoke checklist (sideload APK)

| #   | Check                                                | Pass? |
| --- | ---------------------------------------------------- | ----- |
| 1   | Cold start shows CorrelCore UI                       |       |
| 2   | Navigate to login / register                         |       |
| 3   | Offline / network error banner (airplane mode)       |       |
| 4   | App survives process death (recent apps → reopen)    |       |
| 5   | Login succeeds and app stays up (no post-login kill) |       |
| 6   | Deep link `correlcore://entries/new` opens app       |       |
| 7   | Uninstall / reinstall keeps data cleared             |       |

Auth success + create entry = Sprint 3 exit criterion. Post-login must not
crash on sideload APKs without FCM (gated by `PushAvailability`).
