# Release 1.0.x — remaining documentation & version sync

**Date:** 2026-07-19  
**Context:** README refreshed for the `1.0.x` line; completed milestones archived in
[`COMPLETED_MILESTONES.md`](COMPLETED_MILESTONES.md).  
**Git tags present:** `v1.0.0` … `v1.0.5` (latest: Android sideload / FCM gate).

This checklist is the follow-up inventory so the repo *fully* reflects the public
selfhost release line and post-1.0 M11 work. Items are ordered by impact.

---

## P0 — Release honesty

| Item | Current state | Suggested action |
| ---- | ------------- | ---------------- |
| **CHANGELOG `[1.0.1]`–`[1.0.5]`** | Missing; patch work sits under `[Unreleased]` | Add Keep-a-Changelog sections from tag subjects (APK notes, brand, Capacitor reachability, mixed content, FCM/GlitchTip gate) |
| **Manifest versions still `1.0.0`** | `package.json`, `apps/web/package.json`, `backend/pyproject.toml`, i18n `app.version`, `export_service.APP_EXPORT_VERSION` | Decide: bump to **`1.0.5`** on `main`, or document “manifests = minor line, tags = patches” |
| **docs-site status blurb** | Still “approaching v1.0” / “pre-alpha badge” (`docs-site/docs/index.md`) | State **released `1.0.x`**; badge is “Selfhost · Open Source” |
| **Install image pins** | Examples use only `IMAGE_TAG=v1.0.0` | Recommend latest `v1.0.x` (e.g. `v1.0.5`) in INSTALL + container-images (+ docs-site mirrors) |

## P1 — Design doc & roadmap truth

| Item | Current state | Suggested action |
| ---- | ------------- | ---------------- |
| **`DESIGN_DOCUMENT.md` header** | Version `0.14`, date 2026-07-10; “Capacitor scaffold” | Bump to post-1.0 summary: M11 sprints 1–5 shipped, Play exit open |
| **Offline language in design doc** | §1.4 / §3.1 still defer sync to M4 / post-M4 | Mark M4.1 Dexie sync **shipped** (feature-flagged) |
| **M4 acceptance checkboxes** | Still unchecked in design doc | Check off or move to historical appendix |
| **M11 acceptance in design doc** | Widget/FCM still open in checklist | Align with [`M11_SPRINT_PLAN.md`](../M11_SPRINT_PLAN.md) |
| **`CLOSEOUT_SPRINT_PLAN.md` M11 row** | Says Sprint 1–3 only | Update to 1–5 complete |
| **`M10_SPRINT_STATUS.md`** | Unchecked “push `v1.0.0`” | Mark done; optional `1.0.x` maintenance note |
| **`GO_PUBLIC_CHECKLIST.md`** | Pre-`v1.0.0` framing | Reframe for patch releases + Android APK releases |

## P2 — Frontend / Android status surfaces

| Item | Current state | Suggested action |
| ---- | ------------- | ---------------- |
| **`FRONTEND_STATUS.md`** | Snapshot 2026-06-27; no Capacitor/widget/FCM | Refresh date; add M11 native track or link M11 plan; split FCM (M11) vs UnifiedPush (M4.2) |
| **`apps/android/README.md`** | Still “M11 Sprint 1” framing | Reflect sprints 1–5 + open Play/ops (#429) |
| **`docs/features/PWA.md`** | Glance widget “later” | Note Glance shipped (M11 Sprint 4) |
| **`ANDROID_SIDELOAD.md` version examples** | `1.0.0-android.1` / code `2` | Match CI tag → `versionName` / `versionCode` derivation |
| **Android `package.json` `0.0.0` / Gradle defaults `1.0.0`** | Stale vs tagged APKs | Align defaults or document “CI tag overrides” |
| **`infra/docker/.env.example` `APP_VERSION=1.0.0`** | Pin | Match current release or “same as IMAGE_TAG” |

## P3 — Beta / historical framing

| Item | Current state | Suggested action |
| ---- | ------------- | ---------------- |
| **`BETA_ONBOARDING.md` / `BETA_CHECKLIST.md`** | “pre-release” / timeline to M10 | Archive as M9 historical or reframe for post-1.0 closed testing |
| **`M4_VISUAL_QA.md`** | Defers Dexie to M4.1 | Add “superseded — M4.1 complete” banner |
| **Upgrade guide title** | “M10 Compose Upgrade Guide” | Add `1.0.x` patch upgrade path |

## Already aligned (no action)

- [`SECURITY.md`](../../SECURITY.md) — supports `1.0.x`
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — selfhost v1.0 released
- Landing UI — “Selfhost · Open Source” (no pre-alpha)
- Docs-site user-guide PWA/offline section — Dexie when enabled
- Root README (this PR) — logo, active roadmap, archived completed milestones

---

## Suggested sync order

1. CHANGELOG sections for `1.0.1`–`1.0.5`
2. Manifest / export / i18n version policy
3. docs-site index + install image pins
4. `DESIGN_DOCUMENT.md` header + offline/M11 acceptance
5. `FRONTEND_STATUS.md` + Android README
6. Beta docs reframe / archive banners
