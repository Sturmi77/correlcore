# M7 Sprint Plan - Insights v2

Last updated: 2026-05-31

M7 opens the post-M5 analytics track. It extends the M3 insight engine with
multivariate models, lag analysis, symptom analytics, and clustering while
keeping Android, Health Connect, and sleep import in M8.

Primary references:

- [`M7_NOTES.md`](M7_NOTES.md)
- [`M7_M8_MILESTONE_SWAP.md`](M7_M8_MILESTONE_SWAP.md)
- [`adr/0016-timeseries-split-ml-models.md`](adr/0016-timeseries-split-ml-models.md)
- [`adr/0025-symptom-analytics.md`](adr/0025-symptom-analytics.md)
- [`features/symptom-analytics.md`](features/symptom-analytics.md)

## Sprint 0 - Milestone Opening

Goal: make M7 trackable before code lands.

- [x] Create M7 sprint plan and status documents.
- [x] Confirm M7 scope after the M7/M8 milestone swap.
- [x] Record GitHub hygiene gap: public milestones still stop at M10 and issues
  #144-#150 still carry historical M8 titles.
- [ ] Create/update GitHub milestone labels and issue titles when write access is
  available outside the read-only `gh` CLI.
- [ ] Move ADR-0025 from Proposed to Accepted before symptom Level 2 work starts.

## Sprint 1 - Lasso & Lag (#144, #145)

Goal: ship the first backend-only Insights v2 slice without changing the public
Insights API envelope.

Scope:

- Add additive `insight_type` support for `symptom_cluster`.
- Extend analytics input rows with symptom presence.
- Build a combined design matrix from metrics, tags, and symptoms.
- Run deterministic `LassoCV` models with `TimeSeriesSplit`.
- Run 1-7 day lag analysis with causal `shift()` plus `dropna()`.
- Store Lasso and lag outputs as `symptom_cluster` insights with
  `payload.method = "lasso" | "lag"`.
- Keep all user-facing statements neutral and non-causal.

Acceptance criteria:

- [x] Lasso runs only with at least 90 daily entries.
- [x] Lasso results are reproducible for fixed input data.
- [x] Symptoms are binary features in the same design matrix as tags and metrics.
- [x] Lag features cover 1-7 days and drop warm-up rows after shifting.
- [x] `TimeSeriesSplit` never trains on future rows.
- [x] Existing M3 insight families remain unchanged.

## Sprint 2 - Symptom Analytics Level 2

Goal: implement Symptom x Tag co-occurrence insights and visualization payloads.

- [x] Add `symptom_mood_association` foundation if not already shipped.
- [x] Compute Phi, Jaccard, Lift, Fisher Exact, and BH-FDR for eligible pairs.
- [x] Extend `/insights` feed rendering with symptom-specific cards and copy.
- [x] Add symptom co-occurrence heatmap payloads and frontend component.

## Sprint 3 - Clustering

Goal: group signals that often appear together.

- [x] Enable pgvector in Alembic.
- [x] Add `tag_vectors` storage and nightly recomputation.
- [x] Add `GET /api/v1/insights/tag-clusters`.
- [ ] Use combined symptom+tag Jaccard distance for symptom-aware clusters (deferred after tag-only Sprint 3 slice).

## Sprint 4 - Optional LLM & Digest

Goal: optional language polish and weekly summary after core analytics are green.

- [ ] Add local-only Ollama integration behind an opt-in switch.
- [ ] Verify DSGVO local-processing requirement.
- [ ] Add weekly digest only after push infrastructure is ready.

## Closeout Gates

- [ ] Backend: `ruff`, `mypy`, `pytest --cov`.
- [ ] Web: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm check:contrast`.
- [ ] Visual QA for `/insights` at 375 px, 768 px, 1280 px in light and dark.
- [ ] Docs and changelog updated.
