# M4 Sprint Status - Quick Wins + Mobile/PWA Hardening

Last updated: 2026-05-29

Tracking document for [`docs/M4_SPRINT_PLAN.md`](M4_SPRINT_PLAN.md). M4 is
rescoped to quick wins and PWA/mobile hardening. Full Dexie offline sync,
sync conflict logs, Capacitor, Web Push, and Notes Composer are follow-ups
after M4.

**Milestone completeness:** Implementation merged on `main` (PR #211). Closeout
(QA sign-off, issue rescope, CI confirmation) is still in verification.

## Overview

| Sprint | Title                                | Status          |
| ------ | ------------------------------------ | --------------- |
| 0      | ADR & Scope Documentation            | Done            |
| 1      | Entry Slots + Trend Smoothing        | Done            |
| 2      | Guided Onboarding + Cycle Groundwork | Done            |
| 3      | Developer Mode                       | Done            |
| 4      | PWA Hardening                        | Done            |
| 5      | Closeout                             | In verification |

## Sprint 0 - Done

- [x] ADR-0028 documents existing `entries.slot` as the canonical time-slot field.
- [x] ADR-0029 documents client-side 7-day SMA smoothing.
- [x] ADR-0030 documents guided onboarding custom-tag creation by slug.
- [x] ADR-0031 documents neutral `cycle_day` scope.
- [x] `docs/DESIGN_DOCUMENT.md` reflects the M4 quick-win rescope.

## Sprint 1 - Done

- [x] `EntryUpdate.slot` accepted by backend schemas and service updates.
- [x] Slot-update uniqueness conflicts map to HTTP `409`.
- [x] Entry form/sheet exposes Morning / Noon / Evening chips behind `+ More`.
- [x] Delta lookup follows the selected slot.
- [x] Trends Mood has `Raw | Smoothed` for 30D+ ranges using `cc_trend_smooth`.
- [x] SMA edge cases are covered by unit tests.

## Sprint 2 - Done

- [x] Migration `013_add_cycle_day_to_entries.py` adds nullable `entries.cycle_day`.
- [x] Entry create/update/read schemas include `cycle_day` with `1..35` validation.
- [x] `GET /api/v1/onboarding/tag-suggestions` returns grouped suggestions.
- [x] `POST /api/v1/onboarding/complete` creates/reuses custom tags by slug and sets existing onboarding preferences.
- [x] `/onboarding` implements a 3-step guided flow with skip, tag picker, and summary.
- [x] Cycle day field is available behind `+ More`.
- [x] Trends Health shows neutral cycle-day context when data exists.

## Sprint 3 - Done

- [x] `devPhase` store is in-memory only.
- [x] Settings > Developer includes phase switcher, onboarding-state toggle, and entry-count mock.
- [x] Insight store reads Dev Mode maturity overrides when visual mocks are forced.
- [x] Onboarding preview opens from Settings in a modal iframe.
- [x] Disabling Dev Mode resets all overrides.

## Sprint 4 - Done

- [x] `pwaInstallStore` captures `beforeinstallprompt`.
- [x] Home shows a dismissible install banner persisted via `cc_pwa_dismissed`.
- [x] `/offline` fallback route added.
- [x] Service Worker caches app shell/static resources and skips `/api/*`.
- [x] Manifest, app icon, and iOS PWA meta tags reviewed.
- [x] `docs/features/PWA.md` documents install/offline behavior.

## Sprint 5 - In Verification

- [x] `docs/FRONTEND.md` updated for M4 user-visible surfaces.
- [x] `CHANGELOG.md` updated under Unreleased.
- [x] `docs/quality/M4_VISUAL_QA.md` created with local QA status.
- [ ] Rendered QA signed off at 375/768/1280 in light and dark.
- [ ] GitHub issues #10, #24, #27, and #200 commented/rescoped for follow-up scope.
- [ ] GitHub CI green on final docs/closeout commit.
