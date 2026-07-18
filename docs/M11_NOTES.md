# M11 Notes — Android Play Store & Homescreen Widget

Last updated: 2026-07-18

This document captures the scope and acceptance criteria for the
**Android Play Store** path and the native homescreen widget deferred from M4.

**Execution plan:** [`M11_SPRINT_PLAN.md`](M11_SPRINT_PLAN.md) — phased sprints,
including **pre-Play sideload** via signed GitHub Release APK + Obtainium
(F-Droid deferred).

## Scaffold / shell status

Capacitor Android package under [`apps/android/`](../apps/android/):

- [x] Package + CI config validate (#27)
- [x] Committed native project `apps/android/android/` (Sprint 1)
- [x] Static SPA build (`build:capacitor` → `webDir` `build-capacitor`)
- [x] Capacitor 7.6.7 aligned; brand icons/splash; `correlcore://entries/new`
- [x] CI **Assemble debug APK** (artifact `correlcore-debug-apk`)
- [x] Signed release APK/AAB path + sideload docs (Sprint 2) —
      [`ANDROID_SIDELOAD.md`](selfhost/ANDROID_SIDELOAD.md); live Release asset
      needs repo signing secrets + `v*` tag — ops: [#429](https://github.com/Sturmi77/correlcore/issues/429),
      [`M11_OPS_CHECKLIST.md`](selfhost/M11_OPS_CHECKLIST.md)
- [x] Bearer auth + API base URL (Sprint 3, ADR-0006)
- [ ] Play Store Internal / Closed Testing

Health Connect **consent** foundation shipped with #31 (`consent_log`, Settings Privacy).
Native HC import and Play Data Safety declaration remain M8/M11 exit work.

## Context — Homescreen widget

M4 delivered a **PWA install prompt** and homescreen shortcut (web-based).
A true launcher widget requires the native Android app path and Jetpack Glance.

Deferred rest of M11 because:

1. Play Store closed-testing path must exist on top of the Capacitor shell
2. Glance API is Kotlin/Compose-only — not available in a PWA
3. Widget data must be fetched from the CorrelCore API with WorkManager sync

## Scope (widget track — after shell)

See also [`M11_SPRINT_PLAN.md`](M11_SPRINT_PLAN.md) Sprints 4+.

### Widget Data Endpoint

- `GET /api/v1/widget/summary` — lightweight endpoint for widget use
  - Returns: today's entry status (`has_entry: bool`),
    last 7-day mood average (`mood_avg_7d: float | null`),
    next suggested entry time based on time-slot history
  - Authenticated via existing JWT (widget uses stored token)
  - Response max 1 KB; optimised for frequent polling
- Unit tests: response shape, auth
- `docs/API.md` updated

### Android Glance Widget

- `AppWidget.kt` using Jetpack Glance
- Widget layout:
  - Today's mood average (large number) or "No entry yet"
  - "+ Add entry" button — deep-links to `/entries/new` in the Capacitor WebView
    (`correlcore://entries/new` intent filter landed in Sprint 1)
  - Last updated timestamp (small, muted)
- WorkManager periodic sync (15-minute interval, battery-aware)
- Widget respects system dark/light mode
- `glance-appwidget` dependency + `AndroidManifest` registration

### QA & Play Store

- Widget QA on Android 12/14, 4×1 and 4×2, light/dark
- Play Store listing + closed testing
- `docs/features/WIDGET.md` documents setup and permissions

## Acceptance Criteria

### Scaffold / shell

- [x] Capacitor package present under `apps/android` with CI validate
- [x] Production `cap sync` + debug `assembleDebug` path green
- [x] Signed `assembleRelease` / GitHub Release attach path (Sprint 2)
- [ ] Play Store Internal Testing Track live

### Widget

- [ ] `GET /api/v1/widget/summary` returns correct data within 200 ms
- [ ] Widget renders today's mood average or "No entry yet"
- [ ] "+ Add entry" deep-link opens entry form in the Capacitor app
- [ ] WorkManager sync runs every 15 minutes (battery-aware)
- [ ] Widget renders correctly in light and dark system themes
- [ ] Widget QA passed on Android 12 and Android 14
- [ ] 4×1 and 4×2 size variants display without truncation
- [ ] Play Store listing updated
- [ ] CI green (Android release build)

## Prerequisites

- Capacitor scaffold (#27) — **done**
- Production shell (Sprint 1) — **done**
- `GET /api/v1/widget/summary` endpoint
- Glance API minimum SDK: Android 12 (API 31)
- M4 PWA install prompt shipped

## iOS Note

iOS home-screen widgets are out of scope for M11 (Android-first Play Store).
See also [ADR-0002](adr/0002-capacitor-statt-twa.md) and [ADR-0006](adr/0006-cookie-auth-mit-capacitor-migration.md).
