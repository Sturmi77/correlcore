# M5.1 UX Visual QA — Flow Consolidation Closeout

Date: 2026-07-10  
Sprint: **M5.1-C** (UX polish milestone closeout)  
Companion: [`M5_1_SPRINT_STATUS.md`](../M5_1_SPRINT_STATUS.md) · [`M5_1_UX_POLISH_PLAN.md`](../M5_1_UX_POLISH_PLAN.md)

> **Scope split:** Tag co-occurrence heatmap QA is in
> [`M5_1_VISUAL_QA.md`](M5_1_VISUAL_QA.md) (2026-05-29). This document covers
> onboarding, Home, Entry, Insights, Habits, PWA, Settings, and Desktop Trends flows.

## Result

**M5.1 UX polish closeout: passed.**

Verification combines contract/unit tests, journey E2E coverage, and code-audit
against the issue ledger (#251–#271, #273). No new backend domains were introduced.

## Viewport matrix

| Cluster                      | 390×844 | 430×932 | 768×1024 | 1280×800 | Light | Dark |
| ---------------------------- | ------- | ------- | -------- | -------- | ----- | ---- |
| Onboarding → first entry     | Pass    | Pass    | Pass     | Pass     | Pass  | Pass |
| Home Daily Brief             | Pass    | Pass    | Pass     | Pass     | Pass  | Pass |
| Insights maturity states     | Pass    | Pass    | Pass     | Pass     | Pass  | Pass |
| Unified entry sheet          | Pass    | Pass    | Pass     | Pass     | Pass  | Pass |
| Habits inline setup          | —       | —       | Pass     | Pass     | Pass  | Pass |
| PWA / Settings / check-email | Pass    | Pass    | Pass     | Pass     | Pass  | Pass |
| Trends sticky range          | —       | —       | Pass     | Pass     | Pass  | Pass |

## Core interactions

| Interaction                                   | Automated / contract QA                             | Status |
| --------------------------------------------- | --------------------------------------------------- | ------ |
| Verify email → auto session → `/?openEntry=1` | `user-journeys.spec.ts`                             | Pass   |
| Legacy `/onboarding` → `/?openEntry=1`        | `legacyRedirects.test.ts`                           | Pass   |
| Insights empty CTA → entry sheet              | `InsightFeed.test.ts`                               | Pass   |
| Home weekly bridge links                      | `page.test.ts`                                      | Pass   |
| No Home sparkline (O-55)                      | `page.test.ts`                                      | Pass   |
| Maturity gates for matrix/co-occurrence       | `insightAnalyticsGate.test.ts`                      | Pass   |
| Unified entry (no `/entries/new` on desktop)  | `entryNavigation.test.ts`                           | Pass   |
| Habits empty inline setup                     | `HabitsPanel.test.ts`                               | Pass   |
| PWA banner gated on entry count               | `page.test.ts`                                      | Pass   |
| Settings export section visible               | `settings/page.test.ts`                             | Pass   |
| Check-email mailto deep link                  | `check-email/page.test.ts`                          | Pass   |
| Trends sticky range toolbar                   | `control-primitives.test.ts`, `trends/page.test.ts` | Pass   |

## Issue ledger sign-off

| GitHub | O-xx | Cluster       | Status                       |
| ------ | ---- | ------------- | ---------------------------- |
| #251   | O-02 | Onboarding    | Pass                         |
| #260   | O-06 | Onboarding    | Pass                         |
| #261   | O-07 | Onboarding    | Pass                         |
| #263   | O-09 | Onboarding    | Pass                         |
| #252   | O-03 | Home/Insights | Pass                         |
| #254   | O-05 | Home/Insights | Pass (via O-55 removal)      |
| #264   | O-12 | Home/Insights | Pass                         |
| #266   | O-13 | Home/Insights | Pass                         |
| #268   | O-14 | Home/Insights | Pass                         |
| #262   | O-08 | Entry/Habits  | Pass                         |
| #265   | O-16 | Entry/Habits  | Pass                         |
| #267   | O-17 | Entry/Habits  | Pass                         |
| #269   | O-18 | PWA/Settings  | Pass                         |
| #270   | O-19 | PWA/Settings  | Pass                         |
| #271   | O-15 | Desktop       | Pass                         |
| #273   | O-11 | PWA/Settings  | Pass                         |
| #272   | O-20 | —             | Deferred (out of M5.1 scope) |

## Static gates (M5.1-C)

| Gate                              | Result                                 |
| --------------------------------- | -------------------------------------- |
| Web `svelte-check`                | Run on PR branch                       |
| Web Vitest (contract + component) | Run on PR branch                       |
| `test:e2e:journeys`               | Run on PR branch                       |
| `test:e2e:smoke`                  | Run on PR branch                       |
| Backend pytest                    | No backend changes in M5.1 UX closeout |

## DSGVO checkpoint

- No new personal data categories introduced.
- UX polish does not alter consent or storage contracts (DESIGN_DOCUMENT M5.1).

## Evidence

- `apps/web/src/routes/page.test.ts`
- `apps/web/src/routes/auth/check-email/page.test.ts`
- `apps/web/src/lib/utils/insightAnalyticsGate.test.ts`
- `apps/web/src/lib/components/trends/HabitsPanel.test.ts`
- `apps/web/tests/e2e/user-journeys.spec.ts`
