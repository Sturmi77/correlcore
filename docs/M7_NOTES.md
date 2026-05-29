# M7 Notes — Insights v2

Last updated: 2026-05-29

Implementation notes for **M7 — Insights v2** (Lasso, lag analysis, symptom
analytics, tag clustering, optional Ollama). Milestone resequencing rationale:
[`M7_M8_MILESTONE_SWAP.md`](M7_M8_MILESTONE_SWAP.md).

## Context

M3.x delivers correlation-based insights (tag ↔ metric, weekday patterns).
M5 adds a raw tag co-occurrence heatmap. **M7** extends the pipeline with
multivariate models, lag analysis, full symptom analytics (ADR-0025), and
optional tag clustering — all on existing entry/tag/symptom data, without
Android or Health Connect.

## Scope

### Sprint 1 — Lasso & Lag (#144, #145)

- Lasso regression over tags, metrics, and symptoms (binary features)
- Lag analysis 1–7 days; symptoms as input and target variables
- `TimeSeriesSplit` validation per [ADR-0016](adr/0016-timeseries-split-ml-models.md)
- Minimum n=90 entries before cross-validated models run

### Sprint 2 — Symptom Analytics (Level 2 & 3)

- Symptom×tag co-occurrence (Phi, Jaccard, Lift, Fisher) with FDR (BH)
- Symptom calendar heatmap, co-occurrence heatmap, trend overlay in `/insights`
- Hierarchical clustering (#150) on combined symptom+tag Jaccard matrix
- Full acceptance criteria in [`features/symptom-analytics.md`](features/symptom-analytics.md)

### Sprint 3 — Tag Clustering (pgvector)

- Enable `pgvector` extension in Alembic migration
- Per-tag co-occurrence vectors from M5 aggregation table → `tag_vectors`
- k-means clustering (k=3..6); `GET /api/v1/insights/tag-clusters`
- Insufficient-data guard: < 90 entries or < 5 active tags → `{ "status": "insufficient_data" }`
- Frontend: "Tag Groups" section in Insights

### Sprint 4 — Optional LLM & Digest

- Ollama integration for natural-language insight summaries (opt-in, local only)
- Weekly "Insight Digest" push notification (optional)

## Acceptance Criteria

- [ ] Lasso and lag produce reproducible results on fixed input data
- [ ] Symptom insights integrated in `/insights` feed per ADR-0025
- [ ] `pgvector` migration applied; tag vectors recomputed nightly
- [ ] Cluster cards use copy: "Tags that often appear together" (no "AI"/"ML" language)
- [ ] LLM optional and disableable without feature loss
- [ ] Visual QA at 375 px, 768 px, 1280 px (light + dark)
- [ ] CI green

## Prerequisites

- M3 insight engine shipped
- M5 co-occurrence heatmap / aggregation table
- Sprint-free pointbiserial Symptom↔Mood bugfix (ADR-0025 prerequisite)
- `pgvector` available on Synology NAS Docker image (verify before sprint)

## Deferred to M8

- Sleep×Symptom association (requires sleep metrics from M8)
- Cycle × lifestyle correlations that depend on Health Connect import use
  `cycle_day` from M4/M5 where available; HC sync remains M8
