# M7 Sprint Plan - Insights v2

Last updated: 2026-06-28

M7 opens the post-M5 analytics track. It extends the M3 insight engine with
multivariate models, lag analysis, symptom analytics, and clustering while
keeping Android, Health Connect, and sleep import in M8.

**Milestone states:**

| State               | Meaning                                                 |
| ------------------- | ------------------------------------------------------- |
| **Core shipped**    | Sprints 1–7 on `main` (analytics engine + primary UI)   |
| **Spec complete**   | Sprint 9 — remaining ADR-0025 / visualization spec gaps |
| **Optional polish** | Sprint 8 — Ollama / digest (out of spec-complete scope) |

Detailed Sprint 9 breakdown: [`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md).

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
- [x] Create/update GitHub milestone labels and issue titles when write access is
      available outside the read-only `gh` CLI. (#144/#145 closed and retitled 2026-06-28.)
- [x] Move ADR-0025 from Proposed to Accepted before symptom Level 2 work starts.

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
- [ ] Use combined symptom+tag Jaccard distance for symptom-aware clusters → **Sprint 9 Paket D**.

## Sprint 4 - Optional LLM & Digest (Sprint 8)

Goal: optional language polish and weekly summary after core analytics are green.

- [ ] Add local-only Ollama integration behind an opt-in switch (#148).
- [ ] Verify DSGVO local-processing requirement.
- [ ] Add weekly digest only after push infrastructure is ready (#147).

## Sprint 5 - Closeout Core

Goal: formalise M7 completion for the shipped Sprints 1-3 slice and enable
full-stack QA without developer mock visualizations.

- [x] Accept ADR-0025.
- [x] Add deterministic M7 QA seed (`backend/scripts/seed_m7_qa.py`).
- [x] Document full-stack QA workflow with seed in [`quality/M7_VISUAL_QA.md`](quality/M7_VISUAL_QA.md).
- [x] Add M7 quality gate sign-off in [`quality/M7_QUALITY_GATE.md`](quality/M7_QUALITY_GATE.md).
- [x] Close GitHub issues #144 and #145 with updated M7 titles (2026-06-28).
- [x] Run full-stack validation on `/insights` with seeded user (integration tests + CI;
      optional GUI per [`quality/M7_SPRINT5_FULLSTACK_QA.md`](quality/M7_SPRINT5_FULLSTACK_QA.md)).

Exit: Must-have backend (#144/#145) formally closed; real-data M7 path validated. **Done 2026-06-28.**

## Sprint 6 - Symptom Visualisation Completion

Goal: close remaining frontend acceptance criteria from
[`features/symptom-analytics.md`](features/symptom-analytics.md) and
[`frontend/SYMPTOM_VISUALIZATION.md`](frontend/SYMPTOM_VISUALIZATION.md).

- [x] Implement `SymptomCalendarHeatmap` (year grid per symptom, `early_patterns`).
- [x] Implement `SymptomTrendOverlay` (custom dual-axis SVG, rolling-7d frequency + mood).
- [x] Extend `CorrelationDisclaimer` with symptom Lift methodology copy.
- [x] Add component tests for `TagGroupsSection`, `SymptomAnalyticsSection`,
      `SymptomCooccurrenceHeatmap`.

Exit: All M7 symptom-frontend criteria in the feature spec are met. **Done 2026-06-28.**

## Sprint 7 - Should / Could Analytics

Goal: quality improvements that are not required for a minimal M7 exit but are
listed in the design doc or GitHub backlog.

- [x] #146 Weekday confounder control (OLS regression beyond current heuristic).
- [x] #150 Hierarchical clustering reorder for co-occurrence heatmaps (`robust`).
- [x] Defer #149 Changepoint detection to post-M7 unless beta feedback demands it.

Exit: Should-have issues resolved or explicitly deferred with ADR/issue notes. **Done 2026-06-28.**

## Sprint 9 - Spec Complete (Feature-Complete)

Goal: close all remaining M7 acceptance criteria from ADR-0025 and the symptom
visualization spec **without** sleep, cycle, LLM, or changepoint scope.

Work packages (full detail in [`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md)):

| Paket | Focus                                                                               |
| ----- | ----------------------------------------------------------------------------------- |
| **A** | Interaktion: calendar/heatmap `selectDate` → entry drawer; symptom×tag detail sheet |
| **B** | Feed: confounder-muted `InsightCard`, ranking downgrade                             |
| **C** | Heatmap polish: tag-cluster sort, subscript counts, keyboard/a11y, E2E hooks        |
| **D** | Backend: combined symptom+tag Jaccard clusters (#150 API rest)                      |
| **E** | Docs, spec checkbox sign-off, GitHub hygiene                                        |

- [ ] Paket A — Interaktion & Entry-Drilldown
- [ ] Paket B — Feed Confounder UX
- [ ] Paket C — Heatmap-Polish & Parität
- [ ] Paket D — Kombinierte Cluster-API
- [ ] Paket E — Docs & Spec-Sign-off

Exit: M7 **spec complete** per quality gate; Sprint 8 (LLM) remains optional.

## Sprint 8 - Optional LLM & Digest

Goal: polish layer after M7 exit criteria are green.

- [ ] #148 Ollama integration (opt-in, local only).
- [ ] #147 Weekly insight digest (blocked on M4 push infrastructure).
- [ ] DSGVO LLM checkpoint documented.

## Deferred Scope (not M7 spec-complete)

| Item                                | Target              | Rationale                            |
| ----------------------------------- | ------------------- | ------------------------------------ |
| Cycle x lifestyle correlations      | M7.1                | Product decision + cycle data volume |
| Sleep x symptom analytics           | M8                  | Requires `sleep_minutes`             |
| Notes signal extraction (#201/#202) | M8                  | Separate epic                        |
| Changepoint (#149)                  | Post-M7             | Could-have; `ruptures`               |
| Ollama / weekly digest              | Sprint 8 (optional) | LLM + M4 push                        |

## Closeout Gates

### After Sprints 6–7 (core shipped)

- [x] Backend: `ruff`, `mypy`, `pytest --cov` (Sprint 5 gate).
- [x] Web: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm check:contrast` (Sprint 5 gate).
- [x] Visual QA for `/insights` at 375 px, 768 px, 1280 px in light and dark (mock path).
- [x] Visual QA on full-stack seeded data (automated integration + API verify; optional GUI).
- [x] Docs and changelog updated for M7 core (Sprints 6–7).

### After Sprint 9 (spec complete)

- [ ] Pakete A–E in [`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md) erfüllt.
- [ ] `M7_QUALITY_GATE.md` Verdikt: **M7 spec complete**.
- [ ] SYMPTOM_VISUALIZATION §11 und symptom-analytics §M7 Checkboxen konsistent.
