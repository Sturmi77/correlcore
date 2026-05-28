# M7 Notes — Cycle Tracking Deep Integration

Last updated: 2026-05-28

This document captures the scope and acceptance criteria for the
cycle tracking deep integration deferred from M4.

## Context

M4 Sprint 2 introduces:

- Optional `cycle_day` integer field on `DayEntry`
- `cycle` tag category in the suggestion library
- Neutral cycle day overlay on the Trends > Health tab

M7 extends this with Health Connect (Android) integration and richer
cycle-aware visualisations, once the Android app path is established.

## Scope

### Sprint 1 — Health Connect Read Permission

- Android app requests `READ_MENSTRUATION` Health Connect permission
- Permission request follows the Android Health Connect guidelines
  (rationale screen before the system dialog)
- If permission denied, app falls back to manual `cycle_day` entry
  (M4 behaviour); no error state
- `docs/features/HEALTH_CONNECT.md` documents all requested permissions
  and their purpose

### Sprint 2 — Cycle Data Sync

- Background sync reads menstruation records from Health Connect
- Maps Health Connect `MenstruationRecord` to CorrelCore `cycle_day`
  (day within cycle computed from period start date)
- Sync writes to `cycle_day` on `DayEntry` only if field is currently
  null (manual entry takes precedence)
- `PATCH /api/v1/entries/{id}` source field: `health_connect | manual`
- User can disable Health Connect sync per-field in Settings > Tracking

### Sprint 3 — Cycle-Aware Visualisation

- Trends > Health tab: follicular / ovulatory / luteal / menstrual
  phase bands derived from `cycle_day` (simple 28-day model, clearly
  labelled as approximate)
- Mood overlay on phase bands — colour: `--color-primary` with alpha
- Explicit disclaimer: "Phase bands are approximate and based on a
  28-day model. CorrelCore does not provide medical advice."
- i18n keys `trends.cycle.phases.*`
- Component tests

## Acceptance Criteria

- [ ] Health Connect permission requested with rationale screen
- [ ] Sync writes `cycle_day` only when null (manual wins)
- [ ] User can disable Health Connect sync in Settings
- [ ] Phase bands render with disclaimer text
- [ ] No medical claim language in any visible copy
- [ ] `noGamificationCopy.test.ts` / copy lint passes
- [ ] Visual QA at 375 px, 768 px (light + dark)
- [ ] CI green

## Prerequisites

- Android app shell exists (Play Store path started)
- M4 `cycle_day` field and `cycle` tag category shipped
- Health Connect dependency (`androidx.health.connect:connect-client`)
  added to Android build

## Framing Guardrails

- No algorithmic prediction ("you will ovulate on…")
- No health claim language
- Phase bands always labelled "approximate"
- Disclaimer visible wherever phase bands are shown
