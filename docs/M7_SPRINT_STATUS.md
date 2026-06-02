# M7 Sprint Status - Insights v2

Last updated: 2026-05-31

Tracking document for [`docs/M7_SPRINT_PLAN.md`](M7_SPRINT_PLAN.md).

**Milestone completeness:** M7 is opened. Sprints 1-3 have implementation slices
for Lasso/lag analysis, Symptom Analytics Level 1/2, and tag clustering;
Ollama and digest remain pending.

## Overview

| Sprint | Title                | Status    |
| ------ | -------------------- | --------- |
| 0      | Milestone Opening    | Done      |
| 1      | Lasso & Lag          | In review |
| 2      | Symptom Analytics L2 | In review |
| 3      | Clustering           | In review |
| 4      | Optional LLM/Digest  | Pending   |
| 5      | Closeout             | Pending   |

## Sprint 0 - Done

- [x] `docs/M7_SPRINT_PLAN.md` created.
- [x] `docs/M7_SPRINT_STATUS.md` created.
- [x] M7 scope confirmed as Insights v2 after the milestone swap.
- [x] GitHub hygiene gap recorded: no public M7 milestone is present yet and
      issues #144-#150 still use historical M8 titles.

## Sprint 1 - In Review

- [x] Added additive `symptom_cluster` insight type and Alembic enum migration.
- [x] Added symptom IDs to daily analytics input rows and loader output.
- [x] Added M7 multivariate design matrix with metric, tag, and symptom columns.
- [x] Added deterministic `LassoCV` execution with `TimeSeriesSplit`.
- [x] Added 1-7 day lag analysis using `shift()` and `dropna()`.
- [x] Added backend tests for the n>=90 gate, reproducibility, symptom features,
      causal lag warm-up handling, and symptom target lag analysis.
- [x] Full backend gates completed.
- [ ] PR review completed.

## Sprint 2 - In Review

- [x] Implemented `symptom_mood_association` Level 1 insights.
- [x] Implemented `symptom_tag_cooccurrence` Level 2 insights with Phi, Jaccard,
      Lift, Fisher Exact, and BH-FDR.
- [x] Added symptom-tag co-occurrence API endpoint for `/insights`.
- [x] Added symptom-specific feed titles and symptom-tag heatmap UI.
- [x] Added backend tests for frequency guards, FDR metadata, lift surfacing,
      service output, and endpoint wiring.
- [x] Rendered browser QA completed.
- [ ] PR review completed.

## Sprint 3 - In Review

- [x] Added pgvector-backed `tag_vectors` migration with RLS policies.
- [x] Added 90-day tag co-occurrence vectors and k-means clustering.
- [x] Added nightly tag-vector recompute hook in the analytics worker.
- [x] Added `GET /api/v1/insights/tag-clusters` with insufficient-data guards.
- [x] Added frontend Tag Groups section, API client, mocks, and i18n.
- [x] Rendered browser QA completed for the Tag Groups section in mock/dev mode.
- [ ] Verify pgvector availability in the selfhost Docker target.
- [ ] PR review completed.

## Remaining Work

### Sprint 4

- [ ] Add optional local Ollama integration.
- [ ] Add digest only after push infrastructure is available.
- [ ] Complete DSGVO local-processing verification for LLM output.

## Known Follow-ups

- GitHub milestone and issue hygiene require write access outside this read-only
  agent `gh` environment.
- ADR-0025 is still Proposed and should be accepted before M7 closeout.
- M4/M5 closeout remains separate from the M7 implementation branch.
