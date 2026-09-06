# M11 Ops checklist — signing, sideload & Play Store

Last updated: 2026-09-04

Operator / maintainer work that is **outside the app code sprints**, but required
before or after M11 exit (Play Closed Testing). Engineering sprints 1–2 land
the signed-build _path_; this checklist is the remaining **ops** work.

Related:

- Sideload UX: [`ANDROID_SIDELOAD.md`](ANDROID_SIDELOAD.md)
- Sprint plan: [`../M11_SPRINT_PLAN.md`](../M11_SPRINT_PLAN.md)
- Capacitor shell: [`../../apps/android/README.md`](../../apps/android/README.md)
- **Play Console bootstrap (AP-1 / #719):** [`../runbooks/play-console-bootstrap.md`](../runbooks/play-console-bootstrap.md)

## Why signing secrets stay required

| Phase                         | Need upload/release keystore? | Why                                                                  |
| ----------------------------- | ----------------------------- | -------------------------------------------------------------------- |
| Local / CI **debug** APK      | No                            | Debug key is ephemeral; fine for developers only                     |
| Sideload / GitHub Releases    | **Yes**                       | Same key for every update; otherwise install fails / new app id      |
| Play Internal / Closed / Prod | **Yes**                       | CI uploads AAB with your **upload key** (Play App Signing)           |
| After Play is live            | **Yes**                       | Secrets still drive CI; also keep GitHub APK channel for selfhosters |

You can postpone creating secrets until the first public tester APK — but use
**one** key from that moment on. Do not distribute debug APKs as a long-lived
beta channel.

## Checklist A — Before first public sideload APK

- [ ] Generate upload keystore offline (`keytool`, see ANDROID_SIDELOAD.md)
- [ ] Store `.keystore` encrypted offline (password manager / hardware backup)
- [ ] Add GitHub Actions secrets on `Sturmi77/correlcore`:
  - [ ] `ANDROID_KEYSTORE_BASE64`
  - [ ] `ANDROID_KEYSTORE_PASSWORD`
  - [ ] `ANDROID_KEY_ALIAS`
  - [ ] `ANDROID_KEY_PASSWORD`
- [ ] Dry-run: Actions → **Release — Android (Capacitor)** → `workflow_dispatch`
      (or push a prerelease tag `vX.Y.Z-android.N`)
- [ ] Confirm Release assets: `correlcore-*.apk`, `*.aab`, `SHA256SUMS.txt`
- [ ] Smoke-install APK on a physical device (Android 12+)
- [ ] Repository secret or variable `VITE_API_BASE_URL=https://…/api/v1`
      (required by signed `release-android.yml`; relative `/api/v1` is rejected)
- [ ] Optional: repository secret `PUBLIC_GLITCHTIP_DSN` (or `GLITCHTIP_DSN`) so
      signed/debug Capacitor APKs report JS errors to selfhosted GlitchTip
- [ ] Capacitor build sets absolute API URL for testers
      (`VITE_API_BASE_URL` at `build:capacitor` time; Login/Register „API server“
      field or Settings → App runtime override as fallback)
- [ ] API reachable from the phone (Tailscale/LAN); Capacitor WebView origin
      `https://localhost` is auto-allowed by the API (`cors_allow_origins`)
- [ ] Sideload APK allows cleartext for `http://…/api/v1` selfhost bases

## Checklist B — During M11 engineering (no secrets required)

These proceed without Play / without signing secrets:

- [x] Sprint 1 — Capacitor shell + debug APK CI
- [x] Sprint 2 — signed build path + sideload docs
- [x] Sprint 3 — Bearer auth + API base URL in WebView (code); device smoke open
- [x] Sprint 4 — Widget API + Glance (code); device QA still open — see `docs/features/WIDGET.md`
- [x] Sprint 5 — FCM registration + test endpoint (code); Firebase project / live push open — see `docs/features/PUSH.md`
- [ ] Sprint 6–7 — Play listing / Closed Testing / quality gate

## Checklist B2 — Firebase / FCM (Sprint 5 exit)

- [ ] Create Firebase project; add Android app `de.correlcore.app`
- [ ] Download `google-services.json` → `apps/android/android/app/` (local/CI secret; not git)
- [ ] Create service account with Firebase Cloud Messaging Admin; store JSON as
      API secret `FCM_CREDENTIALS_JSON` (or mount + `GOOGLE_APPLICATION_CREDENTIALS`)
- [ ] Deploy API with `FCM_ENABLED=true` and `uv sync --extra fcm` (or image that
      includes `firebase-admin`)
- [ ] Build Capacitor APK **with** `google-services.json` present, install on a
      Play-services device, log in, accept notification permission
- [ ] `POST /api/v1/devices/push-test` → notification with
      “Time for your daily check-in.”
- [ ] Confirm sideload/GitHub release workflow can still build **without** the
      file (push disabled)

## Checklist C — Play Store (M11 exit / shortly after)

Step-by-step for the first Internal upload:
[`../runbooks/play-console-bootstrap.md`](../runbooks/play-console-bootstrap.md)
(AP-1 / [#719](https://github.com/Sturmi77/correlcore/issues/719)). AP-HC (#718)
Option A is done — upload the **play** AAB (`correlcore-*.aab`), never the
sideload APK.

- [ ] Google Play Console developer account ($25 one-time)
- [ ] Create app `de.correlcore.app` (package id exact)
- [ ] Play App Signing: Google-managed app key + CI keystore as upload key
- [ ] Verify upload-key SHA-256 (`apps/android/scripts/print-upload-cert-fingerprint.sh`)
- [ ] Internal testing track: upload `correlcore-<ver>.aab` from latest `v*` Release
      (first candidate: `v1.7.1` → versionCode `1007001`)
- [ ] Owner install smoke from Internal opt-in link
- [ ] Store listing: short/long description, feature graphic, screenshots (#720)
- [ ] Data Safety form (ADR-0033 / cycle + HC reality — declare only what you ship) (#721)
- [ ] Privacy policy public URL (landing from M10)
- [ ] Pre-Launch Report: no critical crashes (#723)
- [ ] Promote Internal → **Closed Testing** (M11 exit criterion)
- [ ] Optional: link Closed Testing invite in BETA_ONBOARDING

## Checklist D — Post-M11 (optional channels)

- [ ] Keep publishing APK on GitHub Releases for Obtainium / selfhosters
- [ ] F-Droid prep (reproducible build, no-FCM product flavor) — non-blocking
- [ ] Rotate upload key only via Play Console documented process if compromised
- [ ] Document who holds keystore backup (bus factor ≥ 2)

## Suggested GitHub issue title

When filing ops tracking on GitHub, use something like:

> **ops(M11): Android signing secrets, first GitHub Release APK, Play Closed Testing**

Body can link this file and paste checklists A + C.

## Threat / hygiene notes

- Never commit `.keystore`, `keystore.properties`, or base64 blobs to git.
- CI decodes the keystore only into `$RUNNER_TEMP` for the job lifetime.
- Losing the upload key without Play App Signing recovery = cannot update
  sideload installs; with Play App Signing, Google can still issue a new upload key.
