# M5.1 Sprint Status — UX Polish & Flow Consolidation

Last updated: 2026-07-10

Tracking document for [`docs/M5_1_SPRINT_PLAN.md`](M5_1_SPRINT_PLAN.md).

**Milestone completeness:** UX polish closeout complete on `cursor/m5-1-ux-polish-closeout-0ff0`.
Visual QA signed off in [`docs/quality/M5_1_UX_VISUAL_QA.md`](quality/M5_1_UX_VISUAL_QA.md).

**Related:** Tag co-occurrence quick win closed 2026-05-29 —
[`docs/quality/M5_1_VISUAL_QA.md`](quality/M5_1_VISUAL_QA.md).

## Overview

| Sprint | Title                       | Status |
| ------ | --------------------------- | ------ |
| 0      | Scope & audit               | Done   |
| 1      | Onboarding & Entry bridge   | Done   |
| 2      | Home & Insights UX          | Done   |
| 3      | Entry & Habits surfaces     | Done   |
| 4      | PWA, Settings & Desktop     | Done   |
| 5      | Milestone closeout (M5.1-C) | Done   |

## Issue audit matrix

| Issue | O-xx | Status   | Evidence                                                            |
| ----- | ---- | -------- | ------------------------------------------------------------------- |
| #251  | O-02 | Done     | `openEntry.ts`, `GlobalEntrySheet.svelte`, `+page.svelte` auto-open |
| #260  | O-06 | Done     | `OnboardingTagSuggestions.svelte`, ADR-0030 amendment               |
| #261  | O-07 | Done     | `auth.py` verify-email session; `verify-email/+page.svelte`         |
| #263  | O-09 | Done     | `onboarding-habit-hint` in `OnboardingTagSuggestions.svelte`        |
| #252  | O-03 | Done     | `InsightFeed.svelte` → `OPEN_ENTRY_HOME_PATH`                       |
| #254  | O-05 | Done†    | Superseded by O-55 sparkline removal                                |
| #264  | O-12 | Done     | `HomeDailyBrief.svelte` brief-first layout                          |
| #266  | O-13 | Done     | `home-weekly-bridge` in `HomeDailyBrief.svelte`                     |
| #268  | O-14 | Done     | `insightAnalyticsGate.ts`                                           |
| #262  | O-08 | Done     | `entryNavigation.ts`, `/entries/new` redirect                       |
| #265  | O-16 | Done     | `HabitsPanel.svelte` `habits-empty-setup`                           |
| #267  | O-17 | Done     | Heatmap `selectDate` → `EntryHistorySheet`                          |
| #269  | O-18 | Done     | `+page.svelte` PWA gate on `entry_count`                            |
| #270  | O-19 | Done     | `settings-section-export` on Settings hub                           |
| #271  | O-15 | Done     | `trends-sticky-toolbar`, `analysisRange` store                      |
| #273  | O-11 | Done     | `check-email-open-mail` mailto link                                 |
| #272  | O-20 | Deferred | Out of M5.1 scope — backend dependency                              |

† O-55 (Phase 3) removed `HomeSparkline` from Home entirely.

## Completed (by cluster)

### Onboarding & Entry bridge

- [x] Post-onboarding lands on `/?openEntry=1` with `GlobalEntrySheet` open.
- [x] Inline tag suggestions and habit hint on first entry.
- [x] Email verification issues session and redirects without manual login.
- [x] Legacy onboarding routes redirect to canonical funnel.

### Home & Insights UX

- [x] Insights empty-state CTA opens entry sheet inline.
- [x] Home Daily Brief is brief-first with weekly analysis bridge.
- [x] Home sparkline removed (O-55); top-insight snippet in brief (O-56).
- [x] Matrix, co-occurrence, and advanced analytics maturity-gated.

### Entry & Habits surfaces

- [x] Unified desktop/mobile entry via `GlobalEntrySheet`.
- [x] Inline habit setup on empty Habits panel.
- [x] Heatmap drill-down uses `EntryHistorySheet`.

### PWA, Settings & Desktop

- [x] PWA install banner deferred until first entry or retro onboarding complete.
- [x] Export section prominent on Settings hub.
- [x] Check-email mobile mail-app deep link.
- [x] Trends global sticky range control on desktop.

## Closeout (Sprint 5)

- [x] [`M5_1_SPRINT_PLAN.md`](M5_1_SPRINT_PLAN.md) and this status document.
- [x] [`quality/M5_1_UX_VISUAL_QA.md`](quality/M5_1_UX_VISUAL_QA.md) UX flow QA matrix.
- [x] [`M5_1_UX_POLISH_PLAN.md`](M5_1_UX_POLISH_PLAN.md) exit criteria checked.
- [x] `README.md` milestone table updated; M9 positioned as next main milestone.
- [x] Contract tests for PWA gate and check-email mail link.
- [ ] GitHub issues #251–#271, #273 closed (manual/authenticated step).
- [ ] GitHub milestone M5.1 closed (manual/authenticated step).

## Static gates (M5.1-C)

| Gate                | Result           |
| ------------------- | ---------------- |
| `pnpm lint`         | Run on PR branch |
| `pnpm typecheck`    | Run on PR branch |
| `pnpm test`         | Run on PR branch |
| `test:e2e:journeys` | Run on PR branch |
| `test:e2e:smoke`    | Run on PR branch |

## Result

**M5.1 UX Polish & Flow Consolidation: passed.** Product is feature-complete for
the planned MVP UX flows; **M9 (Beta hardening)** is the next main milestone.
