# Release 1.0.x — documentation & version sync

**Date:** 2026-07-19  
**Status:** P0–P2 applied on branch `cursor/release-1-0-x-p0-p2-sync-c06e`  
**Git tags:** `v1.0.0` … `v1.0.5`  
**Manifest line:** **`1.0.5`** (npm / pyproject / i18n / export / Android defaults)

Completed-milestone archive: [`COMPLETED_MILESTONES.md`](COMPLETED_MILESTONES.md).

---

## P0 — Release honesty — done

| Item                          | Resolution                                                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CHANGELOG `[1.0.1]`–`[1.0.5]` | Sections added; post-`v1.0.5` work remains under `[Unreleased]`                                                                                                                 |
| Manifest versions             | Bumped to **`1.0.5`**: root/`apps/web`/`apps/android` `package.json`, `backend/pyproject.toml`, i18n `app.version`, `APP_EXPORT_VERSION`, Gradle defaults (`1.0.5` / `1000005`) |
| docs-site status blurb        | Released `1.0.x` (prior PR commit)                                                                                                                                              |
| Install image pins            | `IMAGE_TAG=v1.0.5` in INSTALL, CONTAINER_IMAGES, docs-site install pages, `.env.example`                                                                                        |

## P1 — Design doc & roadmap truth — done

| Item                              | Resolution                                                                   |
| --------------------------------- | ---------------------------------------------------------------------------- |
| `DESIGN_DOCUMENT.md`              | Version **0.15** (2026-07-19); M11 sprints 1–5; offline/M4.1 shipped wording |
| M4 acceptance checkboxes          | Marked complete                                                              |
| M11 acceptance                    | FCM registration path checked; Play/Firebase ops still open                  |
| `CLOSEOUT_SPRINT_PLAN.md` M11 row | Sprints 1–5 complete                                                         |
| `M10_SPRINT_STATUS.md`            | `v1.0.0` / rc / milestone checkboxes marked done                             |
| `GO_PUBLIC_CHECKLIST.md`          | Historical M10 framing + Post-1.0.x patch section                            |

## P2 — Frontend / Android status — done

| Item                              | Resolution                                                          |
| --------------------------------- | ------------------------------------------------------------------- |
| `FRONTEND_STATUS.md`              | Date 2026-07-19; M11 Capacitor row; FCM vs UnifiedPush split        |
| `apps/android/README.md`          | Sprints 1–5 + Play exit #429                                        |
| `docs/features/PWA.md`            | Glance shipped (M11 Sprint 4)                                       |
| `ANDROID_SIDELOAD.md`             | CI tag → `versionName` / `versionCode` encoding; APK from `v1.0.1+` |
| Android package / Gradle defaults | `1.0.5` / `1000005`                                                 |
| `.env.example`                    | `APP_VERSION=1.0.5`, `IMAGE_TAG=v1.0.5`                             |
| docs-site upgrade guide           | Post-1.0.x image upgrade path; M10 MinIO notes kept as historical   |

## P3 — still optional (not in this pass)

| Item                                       | Notes                                                            |
| ------------------------------------------ | ---------------------------------------------------------------- |
| `BETA_ONBOARDING.md` / `BETA_CHECKLIST.md` | Still “pre-release” framing — reframe or archive when convenient |
| `M4_VISUAL_QA.md` Dexie deferral banner    | Low priority historical QA doc                                   |
| OCI image labels on Dockerfiles            | Optional hardening                                               |

---

## Policy note

Patch tags (`v1.0.1`–`v1.0.5`) and in-repo manifests now agree on **`1.0.5`**.
Future `v1.0.N` tags should: add a CHANGELOG section, bump manifests/i18n/export,
and pin install docs to the new tag (see Post-1.0.x section in
[`GO_PUBLIC_CHECKLIST.md`](../selfhost/GO_PUBLIC_CHECKLIST.md)).
