# M11 Notes — Native Android Homescreen Widget

Last updated: 2026-05-28

This document captures the scope and acceptance criteria for the
native Android homescreen widget deferred from M4.

## Context

M4 Sprint 4 delivers a **PWA install prompt** and homescreen shortcut
(web-based, works on Android Chrome and iOS Safari). A true homescreen
widget — rendered by the Android launcher without opening the app —
requires the native Android app path (TWA or dedicated APK) and the
Android Glance API.

Deferred to M11 because:

1. Native Android app shell must exist (Play Store path)
2. Glance API is Kotlin/Compose-only — not available in a PWA
3. Widget data must be fetched from the CorrelCore API with a
   background sync mechanism (WorkManager)

## Scope

### Sprint 1 — Widget Data Endpoint

- `GET /api/v1/widget/summary` — lightweight endpoint for widget use
  - Returns: today's entry status (`has_entry: bool`),
    last 7-day mood average (`mood_avg_7d: float | null`),
    next suggested entry time based on time-slot history
  - Authenticated via existing JWT (widget uses stored token)
  - Response max 1 KB; optimised for frequent polling
- Unit tests: response shape, auth
- `docs/API.md` updated

### Sprint 2 — Android Glance Widget

- `AppWidget.kt` using Jetpack Glance
- Widget layout:
  - Today's mood average (large number) or "No entry yet"
  - "+ Add entry" button — deep-links to `/entries/new` in the TWA
  - Last updated timestamp (small, muted)
- WorkManager periodic sync (15-minute interval, battery-aware)
- Widget respects system dark/light mode
- `glance-appwidget` dependency added to Android `build.gradle`
- Widget declared in `AndroidManifest.xml` with
  `android:updatePeriodMillis`

### Sprint 3 — QA & Play Store Update

- Widget QA on:
  - Android 12 (API 31) — Glance minimum
  - Android 14 (API 34) — latest stable
  - 4×1 and 4×2 widget sizes
  - Light and dark system themes
- Play Store listing updated with widget screenshot
- `docs/features/WIDGET.md` documents setup, permissions, and
  update interval

## Acceptance Criteria

- [ ] `GET /api/v1/widget/summary` returns correct data within 200 ms
- [ ] Widget renders today's mood average or "No entry yet"
- [ ] "+ Add entry" deep-link opens entry form in TWA
- [ ] WorkManager sync runs every 15 minutes (battery-aware)
- [ ] Widget renders correctly in light and dark system themes
- [ ] Widget QA passed on Android 12 and Android 14
- [ ] 4×1 and 4×2 size variants display without truncation
- [ ] Play Store listing updated
- [ ] CI green (Android build)

## Prerequisites

- Native Android app (TWA or APK) published on Play Store
- `GET /api/v1/widget/summary` endpoint live
- Glance API minimum SDK: Android 12 (API 31)
- M4 PWA install prompt shipped (establishes web homescreen baseline)

## iOS Note

iOS home screen widgets require a native Swift/SwiftUI app and the
WidgetKit framework. This is out of scope for M11 and will be
assessed separately when an iOS app path is planned.
