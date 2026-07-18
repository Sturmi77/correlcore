# M11 Ops checklist — signing, sideload & Play Store

Last updated: 2026-07-18

Operator / maintainer work that is **outside the app code sprints**, but required
before or after M11 exit (Play Closed Testing). Engineering sprints 1–2 land
the signed-build _path_; this checklist is the remaining **ops** work.

Related:

- Sideload UX: [`ANDROID_SIDELOAD.md`](ANDROID_SIDELOAD.md)
- Sprint plan: [`../M11_SPRINT_PLAN.md`](../M11_SPRINT_PLAN.md)
- Capacitor shell: [`../../apps/android/README.md`](../../apps/android/README.md)

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
- [ ] Capacitor build sets absolute API URL for testers
      (`VITE_API_BASE_URL=https://…/api/v1` at `build:capacitor` time, or
      Settings → App runtime override)
- [ ] API `CORS_ORIGINS` includes the Capacitor WebView origin
      (`https://localhost` with `androidScheme: https` in capacitor.config.ts)

## Checklist B — During M11 engineering (no secrets required)

These proceed without Play / without signing secrets:

- [x] Sprint 1 — Capacitor shell + debug APK CI
- [x] Sprint 2 — signed build path + sideload docs
- [ ] Sprint 3 — Bearer auth + API base URL in WebView
- [x] Sprint 4 — Widget API + Glance (code); device QA still open — see `docs/features/WIDGET.md`
- [ ] Sprint 5 — FCM (needs Firebase project — separate ops)
- [ ] Sprint 6–7 — Play listing / Closed Testing / quality gate

## Checklist C — Play Store (M11 exit / shortly after)

- [ ] Google Play Console developer account ($25 one-time)
- [ ] Create app `de.correlcore.app` (or confirm package id)
- [ ] Decide Play App Signing: Google-managed app key + your upload key (recommended)
- [ ] Internal testing track: upload AAB from CI Release artifact
- [ ] Store listing: short/long description, feature graphic, screenshots
- [ ] Data Safety form (ADR-0033 / cycle + HC reality — declare only what you ship)
- [ ] Privacy policy public URL (landing from M10)
- [ ] Pre-Launch Report: no critical crashes
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
