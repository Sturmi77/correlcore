# M8 Notes — Sleep & Health Connect

Last updated: 2026-07-16

Implementation notes for **M8 — Schlaf & Health Connect** (manual sleep
fields, wearable import, sleep↔mood insights, cycle HC deep integration).
Milestone resequencing: [`M7_M8_MILESTONE_SWAP.md`](M7_M8_MILESTONE_SWAP.md).

## Status (M8 core shipped, Sprints 1–5)

The M8 **core** landed via #172 (Sprints 1–5) — see
[`M8_SPRINT_STATUS.md`](M8_SPRINT_STATUS.md) and
[`quality/M8_QUALITY_GATE.md`](quality/M8_QUALITY_GATE.md):

- Manual sleep fields (`sleep_minutes`, `sleep_quality`) on entries + API/sync/export.
- Sleep↔mood correlation in the insight feed (+ sleep columns in the Lasso matrix).
- Native Health Connect bridge (custom Kotlin plugin, [ADR-0042](adr/0042-health-connect-bridge-strategy.md))
  with the `/health-connect` rationale screen.
- Consent-gated sleep import (`POST /api/v1/health-connect/import`, manual-wins,
  per-field toggle, in-app "Sync now").

**Deferred / split out:** Cycle Health Connect + phase bands (own sub-milestone),
Sleep×Symptom, heart-rate persistence, extended sleep fields, and the native
WorkManager background sync. The **native path is not built in CI** (no Android
SDK) — device QA precedes any sideload/Play release. Play Data-Safety declaration
stays with the Play exit.

Open decisions tracker: [`docs/quality/OPEN_DECISIONS_AND_BACKLOG_2026-07-16.md`](quality/OPEN_DECISIONS_AND_BACKLOG_2026-07-16.md).

## Context

M7 delivers analytics on existing self-reported data. **M8** adds sleep metrics
(manual first, then Health Connect on Android) and extends the M7 insight
engine with sleep columns. Cycle deep integration (HC menstruation sync,
phase bands) ships here together with the Android path (M11).

## Scope

### Sprint 1 — Manual Sleep Fields

- Entry fields: `sleep_minutes`, `sleep_quality` (Issue #172 rescoped from M3.5)
- Alembic migration; API + export `sleep: []` populated
- Sleep↔mood correlation in insights feed

### Sprint 2 — Health Connect (Android)

- Permission request with rationale screen (Schlaf + HR only; no movement profiles)
- Background sync from Health Connect sleep records
- `docs/features/HEALTH_CONNECT.md` documents all permissions
- DSGVO: Art. 9 explicit consent before first import — **consent foundation landed**
  (`consent_log` migration 025, consents API, Settings UI). **Import/sync not
  landed** — blocked on M8 Sprint 2 + M11 Android shell.

### Sprint 3 — Sleep×Symptom & Cycle HC

- Sleep×Symptom Spearman when sleep data available (ADR-0025 Level 1 extension)
- `READ_MENSTRUATION` permission; sync `MenstruationRecord` → `cycle_day` when null
- Manual `cycle_day` wins over HC sync
- Settings toggle to disable HC sync per field
- Trends > Health: follicular / ovulatory / luteal / menstrual phase bands (28-day model, disclaimer)

## Acceptance Criteria

- [ ] Health Connect permission requested with rationale screen
- [ ] Import limited to sleep + HR (technically enforced)
- [ ] Sync writes `cycle_day` only when null (manual wins)
- [ ] User can disable Health Connect sync in Settings
- [ ] Sleep×Symptom insights when sleep metrics present
- [ ] Phase bands render with disclaimer; no medical claim language
- [ ] Account delete removes imported HC data
- [ ] `noGamificationCopy.test.ts` / copy lint passes
- [ ] Visual QA at 375 px, 768 px (light + dark)
- [ ] CI green

## Prerequisites

- M7 insight engine (sleep columns extend design matrix, no rewrite)
- Android app shell / Capacitor path (M11 for Play Store HC declaration)
- M4 `cycle_day` field and `cycle` tag category shipped
- `androidx.health.connect:connect-client` in Android build

## Framing Guardrails

- No algorithmic ovulation prediction
- Phase bands always labelled "approximate"
- Disclaimer visible wherever phase bands are shown
