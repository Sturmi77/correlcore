# M7 Sprint 9 Visual QA — Closeout Sign-off

Date: 2026-06-30  
Sprint: **M7-C** (milestone closeout)  
Companion: [`M7_SPRINT9_PLAN.md`](../M7_SPRINT9_PLAN.md) · [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md)

## Scope

Sprint 9 interaction and polish surfaces on `/insights`:

- Entry-history drawer from symptom calendar and comparison heatmap
- Symptom×tag co-occurrence detail sheet (Phi, Jaccard, Lift, confounder hint)
- Confounder-muted insight cards and ranking tie-break in feed
- Tag co-occurrence cluster sort toggle (`robust` phase)
- Mixed tag+symptom signal clusters (`members[]` API)
- Keyboard navigation on heatmap grids (`data-testid` hooks for E2E)

## Verification method

| Layer | Evidence | Date |
| ----- | -------- | ---- |
| Backend unit + integration | `pytest` green; `test_m7_qa_seed_integration.py` in CI | 2026-06-28 |
| Seeded API path | `scripts/seed_m7_qa.py --reset` + `scripts/verify_m7_qa_api.py` | 2026-06-28 |
| Web unit | Vitest component tests (heatmaps, detail sheet, ranking) | 2026-06-28 |
| E2E smoke | `pnpm --filter @correlcore/web test:e2e:smoke` | 2026-06-28 |
| Mobile touch flow | `m7-insights-mobile.spec.ts` | 2026-06-28 |
| Rendered browser (seed user) | Manual smoke on `m7-qa@localhost.dev` post M7-C gates | 2026-06-30 |

## Viewport matrix

| Surface | 375 | 768 | 1280 | Light | Dark |
| ------- | --- | --- | ---- | ----- | ---- |
| Insights feed + confounder cards | Pass | Pass | Pass | Pass | Pass |
| Symptom calendar → entry drawer | Pass | — | — | Pass | Pass |
| Symptom×tag detail sheet | Pass | Pass | — | Pass | Pass |
| Tag cluster sort toggle | Pass | Pass | Pass | Pass | Pass |
| Mixed signal clusters section | Pass | Pass | Pass | Pass | Pass |
| Heatmap keyboard focus | Pass | Pass | Pass | Pass | Pass |

## Core interactions

| Interaction | Status |
| ----------- | ------ |
| Calendar cell tap → entry drawer | Pass |
| Heatmap cell tap → detail sheet with backend fields | Pass |
| Confounded card muted variant + subtitle | Pass |
| Non-confounded ranks above confounded at equal effect | Pass |
| Tag heatmap cluster reorder at `robust` | Pass |
| Mixed cluster members show tag + symptom kinds | Pass |
| No raw p-values in UI (FDR `*` only) | Pass |

## Static gates (M7-C)

| Gate | Result |
| ---- | ------ |
| GitHub CI on `main` (post #238) | Pass (2026-06-28) |
| Local `.\scripts\local-quality.ps1` | Rerun on contributor machine before merge |

## Result

**M7 Sprint 9 visual QA: passed.** Milestone M7 closeout criterion met for spec-complete UX.
