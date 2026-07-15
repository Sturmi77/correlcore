# M7 Sprint Status - Insights v2

Last updated: 2026-06-30

Tracking document for [`docs/M7_SPRINT_PLAN.md`](M7_SPRINT_PLAN.md).

**Milestone completeness:**

| Level | Status |

| ----- | ------ |

| **Core shipped** (Sprints 1–7) | **Done** |

| **Spec complete** (Sprint 9) | **Done** (2026-06-28) |

| **Milestone closeout** (Sprint M7-C) | **Done** (2026-06-30) |

| **Optional** (Sprint 8 LLM/Digest) | Deferred → M7-S8 |

## Overview

| Sprint | Title | Status |

| ------ | -------------------------- | -------------- |

| 0 | Milestone Opening | Done |

| 1 | Lasso & Lag | Done (on main) |

| 2 | Symptom Analytics L2 | Done (on main) |

| 3 | Clustering | Done (on main) |

| 4 | Optional LLM/Digest | Pending → S8 |

| 5 | Closeout Core | **Done** |

| 6 | Symptom Visualisation | **Done** |

| 7 | Should/Could Analytics | **Done** |

| 8 | Optional LLM/Digest | Deferred → M7-S8 |

| 9 | Spec Complete | **Done** |

| M7-C | Milestone Closeout | **Done** |

## Sprint 9 - Done (Spec Complete)

Full plan: [`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md).

| Paket | Focus | Status |

| ----- | ----- | ------ |

| A | Interaktion: entry drawer + symptom×tag detail sheet | Done |

| B | Feed confounder UX (muted card, sort downgrade) | Done |

| C | Heatmap polish: tag cluster sort, a11y, E2E hooks | Done |

| D | Combined symptom+tag Jaccard clusters API (#150 rest) | Done |

| E | Docs, spec sign-off, GitHub hygiene | Done |

**Excluded from Sprint 9:** sleep (M8), cycle (M7.1), LLM/digest (S8), changepoint (#149).

## Sprint 5 - Done

- [x] ADR-0025 accepted (2026-06-28).

- [x] M7 QA seed: `backend/scripts/seed_m7_qa.py` + `m7_qa_seed_service.py`.

- [x] M7 quality gate doc: [`docs/quality/M7_QUALITY_GATE.md`](quality/M7_QUALITY_GATE.md).

- [x] Full-exit sprint plan (Sprints 5–9) in [`M7_SPRINT_PLAN.md`](M7_SPRINT_PLAN.md).

- [x] Close GitHub issues #144 and #145 (2026-06-28).

- [x] Full-stack validation: integration tests + CI + API verify script.

      Sign-off: [`docs/quality/M7_SPRINT5_FULLSTACK_QA.md`](quality/M7_SPRINT5_FULLSTACK_QA.md).

## Sprint 6 - Done

- [x] `SymptomCalendarHeatmap` — Monday-aligned contribution grid per eligible symptom.

- [x] `SymptomTrendOverlay` — rolling-7d symptom frequency + mood dual-axis SVG chart.

- [x] `CorrelationDisclaimer` section 5 — symptom Lift methodology copy (en/de).

- [x] Component tests: `TagGroupsSection`, `SymptomAnalyticsSection`,

      `SymptomCooccurrenceHeatmap`, `symptomAnalyticsViews` utils.

- [x] Web quality gate: `pnpm lint`, `pnpm typecheck`, `pnpm test`.

## Sprint 7 - Done

- [x] #146 Weekday OLS confounder — `weekday_confounder.py` with Newey-West HAC.

- [x] #150 Hierarchical heatmap reorder on `SymptomCooccurrenceHeatmap` (`robust`).

- [x] #149 Changepoint deferred to post-M7.

- [x] Confounder muting on symptom×tag heatmap cells.

- [x] Backend + frontend tests for OLS confounder and cluster ordering.

## Sprint 0 - Done

- [x] `docs/M7_SPRINT_PLAN.md` created.

- [x] `docs/M7_SPRINT_STATUS.md` created.

- [x] M7 scope confirmed as Insights v2 after the milestone swap.

- [x] GitHub hygiene gap recorded: issues #144-#150 still use historical M8 titles.

## Sprint 1 - Done

- [x] Added additive `symptom_cluster` insight type and Alembic enum migration.

- [x] Added symptom IDs to daily analytics input rows and loader output.

- [x] Added M7 multivariate design matrix with metric, tag, and symptom columns.

- [x] Added deterministic `LassoCV` execution with `TimeSeriesSplit`.

- [x] Added 1-7 day lag analysis using `shift()` and `dropna()`.

- [x] Added backend tests for the n>=90 gate, reproducibility, symptom features,

      causal lag warm-up handling, and symptom target lag analysis.

- [x] Merged on `main` (PR #223).

## Sprint 2 - Done

- [x] Implemented `symptom_mood_association` Level 1 insights.

- [x] Implemented `symptom_tag_cooccurrence` Level 2 insights with Phi, Jaccard,

      Lift, Fisher Exact, and BH-FDR.

- [x] Added symptom-tag co-occurrence API endpoint for `/insights`.

- [x] Added symptom-specific feed titles and symptom-tag heatmap UI.

- [x] Rendered browser QA completed (mock path).

- [x] Merged on `main` (PR #223).

## Sprint 3 - Done

- [x] Added pgvector-backed `tag_vectors` migration with RLS policies.

- [x] Added 90-day tag co-occurrence vectors and k-means clustering.

- [x] Added nightly tag-vector recompute hook in the analytics worker.

- [x] Added `GET /api/v1/insights/tag-clusters` with insufficient-data guards.

- [x] Added frontend Tag Groups section, API client, mocks, and i18n.

- [x] pgvector in selfhost Docker (`pgvector/pgvector:pg16` in compose files).

- [x] Merged on `main` (PR #223, #224).

- [x] Combined symptom+tag Jaccard clusters — Sprint 9 Paket D (PR #238).

## Sprint M7-C - Done (2026-06-30)

- [x] Closeout plan with audit findings: [`CLOSEOUT_SPRINT_PLAN.md`](CLOSEOUT_SPRINT_PLAN.md).
- [x] Quality gate updated to **M7 Complete**: [`quality/M7_QUALITY_GATE.md`](quality/M7_QUALITY_GATE.md).
- [x] Sprint 9 visual QA sign-off: [`quality/M7_SPRINT9_VISUAL_QA.md`](quality/M7_SPRINT9_VISUAL_QA.md).
- [x] GitHub issues #146 and #150 closed (shipped Sprints 7/9).
- [x] #149, #147, #148 documented as deferred (post-M7 / M7-S8).
- [x] `README.md` and `CHANGELOG.md` updated for M7 Complete.

## Deferred at M7 closeout (status update 2026-07-15)

| Topic                     | Target / status                                              | Issues                                                     |
| ------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- |
| Ollama + weekly digest    | **Foundation landed** (API + worker); Push-Delivery → M4.2   | #148, #147                                                 |
| Changepoint detection     | **Foundation landed** in analytics pipeline                  | #149                                                       |
| Cycle×lifestyle analytics | M7.1                                                         | [`features/cycle-tracking.md`](features/cycle-tracking.md) |
| Sleep×symptom             | M8                                                           | [`M8_NOTES.md`](M8_NOTES.md)                               |
| M4/M5 formal closeout     | Done — see [`CLOSEOUT_SPRINT_PLAN.md`](CLOSEOUT_SPRINT_PLAN.md) | —                                                       |
