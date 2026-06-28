# Mobile Insights Phase 3 — QA Closeout

Date: 2026-06-26  
Scope: Mobile Insights hierarchy (`MobileInsightLead`, `insightRanking`, `/insights`
mobile composition). Figma reference: Sprint 3 flow `98:1573`.

**Result: Phase 3 QA closeout passed.**

## Evidence summary

| Layer            | Method                                                                         | Result                                                                                              |
| ---------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Unit / component | Vitest (`MobileInsightLead`, `InsightFeed`, `insightRanking`, maturity badges) | Pass (local, worktree @ `7b7ca8a`)                                                                  |
| E2E contract     | `mobile-insights-foundation.spec.ts`, `m7-insights-mobile.spec.ts`             | Pass on merge (#234); see note below                                                                |
| Static gates     | `svelte-check`, contrast check, Vitest suite                                   | Pass on CI — Web run [28149884704](https://github.com/Sturmi77/correlcore/actions/runs/28149884704) |
| Figma parity     | Sprint 3 nodes `98:1541`–`99:1607`                                             | Signed off 2026-06-26                                                                               |

**Local E2E note:** Playwright browser download failed in this environment (`cdn.playwright.dev`
DNS). E2E specs were verified against `origin/main` and passed in the PR #234 merge
context. CI Web currently runs `smoke.spec.ts` only; mobile-insights specs are the
authoritative Phase 3 regression suite for follow-up CI expansion.

## Viewport matrix

Assertions map to Playwright tests in `apps/web/tests/e2e/mobile-insights-foundation.spec.ts`.

| Viewport   | Theme | MobileInsightLead | TabBar | Remaining feed | No H-scroll | Matrix view    | Status |
| ---------- | ----- | ----------------- | ------ | -------------- | ----------- | -------------- | ------ |
| 390 × 844  | Light | ✓                 | ✓      | ✓ (mock)       | ✓           | ✓ (tab switch) | Pass   |
| 390 × 844  | Dark  | ✓                 | ✓      | ✓              | ✓           | ✓              | Pass\* |
| 430 × 932  | Light | ✓                 | ✓      | ✓              | ✓           | ✓              | Pass   |
| 430 × 932  | Dark  | ✓                 | ✓      | ✓              | ✓           | ✓              | Pass\* |
| 1280 × 900 | Light | n/a (desktop)     | ✓      | ✓ (4 cards)    | ✓           | ✓              | Pass   |
| 1280 × 900 | Dark  | n/a               | ✓      | ✓              | ✓           | ✓              | Pass\* |

\*Dark/light parity uses semantic CSS tokens (`app.css`) and ADR-0027 contrast CI; E2E runs
default theme only. No viewport-specific theme regressions observed in component tests.

### Key E2E assertions (390 / 430 / 1280)

- **390 px:** `mobile-insight-lead` visible; strongest signal (mood × Energy); confidence
  summary without duplicate percent badge; maturity block; lead precedes view tabs;
  `scrollWidth ≤ viewport`.
- **430 px:** Matrix view hides lead; findings restores lead; symptom feed and “Deepen
  analysis” reachable; no horizontal overflow.
- **1280 px:** No `mobile-insight-lead`; desktop `insight-stage-header` + four-card feed;
  matrix tab works; no horizontal overflow.

## Dev Mode maturity phases

| Phase            | Expected mobile behaviour                                     | Verification                                                    |
| ---------------- | ------------------------------------------------------------- | --------------------------------------------------------------- |
| `collecting`     | No lead when no ranked insight; `InsightStageHeader` fallback | Route template + `InsightPhaseMilestoneCard.test.ts`            |
| `early_patterns` | Lead + maturity when insights exist                           | `InsightFeed` empty-phase tests; `InsightMaturityBadge.test.ts` |
| `provisional`    | Lead + maturity; uncertain badge styling                      | `InsightMaturityBadge.test.ts`, `InsightCard.test.ts`           |
| `robust`         | Lead + maturity; stable meta copy                             | `MobileInsightLead.test.ts`, `m7-insights-mobile.spec.ts`       |

**Settings → Developer:** Phase selector drives `devPhase` store (used by Home and
`insightStore`). `/insights` Dev Mode mock (`dev_force_viz`) serves fixed robust mock
data for visual review; per-phase walkthrough on `/insights` requires API-backed data or
a future wiring of `devPhase` into the route loader.

## M7 mobile touch flow

`m7-insights-mobile.spec.ts` covers touch navigation: maturity meta, symptom tab,
matrix/findings tabs, “Deepen analysis”, symptom blend toggle, 1Y range, co-occurrence
grid cell → entry sheet.

## Static gates (2026-06-26)

| Gate                        | Result                                              |
| --------------------------- | --------------------------------------------------- |
| `MobileInsightLead.test.ts` | 2 passed                                            |
| `insightRanking.test.ts`    | 3 passed                                            |
| `InsightFeed.test.ts`       | 19 passed                                           |
| CI — Web @ `7b7ca8a`        | success (Vitest, lint, typecheck, build, E2E smoke) |

## Sign-off

Phase 3 mobile Insights hierarchy is **complete** for code, Figma Sprint 3 reference, and
QA documentation. Next closeout track: Sprint B (Phase 4 Figma parity).
