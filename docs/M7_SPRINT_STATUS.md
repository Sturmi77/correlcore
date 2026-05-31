# M7 Sprint Status - Insights v2

Last updated: 2026-05-31

Tracking document for [`docs/M7_SPRINT_PLAN.md`](M7_SPRINT_PLAN.md).

**Milestone completeness:** M7 is opened. Sprint 1 has a backend-only
implementation slice for Lasso and lag analysis; frontend symptom cards,
co-occurrence, clustering, Ollama, and digest remain pending.

## Overview

| Sprint | Title                | Status      |
| ------ | -------------------- | ----------- |
| 0      | Milestone Opening    | Done        |
| 1      | Lasso & Lag          | In review   |
| 2      | Symptom Analytics L2 | Pending     |
| 3      | Clustering           | Pending     |
| 4      | Optional LLM/Digest  | Pending     |
| 5      | Closeout             | Pending     |

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

## Remaining Work

### Sprint 2

- [ ] Implement `symptom_mood_association` if it is still not shipped.
- [ ] Implement `symptom_tag_cooccurrence` with Phi, Jaccard, Lift, Fisher Exact,
  and BH-FDR.
- [ ] Add symptom-specific insight card copy and methodology disclaimer.
- [ ] Add `/insights` symptom co-occurrence visualization.

### Sprint 3

- [ ] Verify pgvector availability in the selfhost Docker target.
- [ ] Add `tag_vectors` storage and nightly recomputation.
- [ ] Add tag cluster endpoint and frontend "Tag Groups" section.

### Sprint 4

- [ ] Add optional local Ollama integration.
- [ ] Add digest only after push infrastructure is available.
- [ ] Complete DSGVO local-processing verification for LLM output.

## Known Follow-ups

- GitHub milestone and issue hygiene require write access outside this read-only
  agent `gh` environment.
- ADR-0025 is still Proposed and should be accepted before Sprint 2 changes.
- M4/M5 closeout remains separate from the M7 implementation branch.
