# M7 Notes — Insights v2

Last updated: 2026-07-15

Implementation notes for **M7 — Insights v2** (Lasso, lag analysis, symptom
analytics, tag clustering, optional Ollama). Milestone resequencing rationale:
[`M7_M8_MILESTONE_SWAP.md`](M7_M8_MILESTONE_SWAP.md).

Sprint tracking: [`M7_SPRINT_PLAN.md`](M7_SPRINT_PLAN.md),
[`M7_SPRINT_STATUS.md`](M7_SPRINT_STATUS.md),
[`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md) (spec-complete closeout).

## Context

M3.x delivers correlation-based insights (tag ↔ metric, weekday patterns).
M5 adds a raw tag co-occurrence heatmap. **M7** extends the pipeline with
multivariate models, lag analysis, full symptom analytics (ADR-0025), and
optional tag clustering — all on existing entry/tag/symptom data, without
Android or Health Connect.

## Milestone levels

| Level                                      | Sprints | Status                                      |
| ------------------------------------------ | ------- | ------------------------------------------- |
| Core analytics + primary UI                | 1–7     | **Done**                                    |
| Spec complete (ADR-0025 + visualization)   | 9       | **Done**                                    |
| Optional LLM / digest / changepoint        | 8 / post | **Foundation landed** (#147–#149); push → M4.2 |

## Scope (by sprint)

### Sprints 1–3 — Engine & clustering core

- Lasso + lag (#144, #145), symptom L1/L2, tag vectors + k-means
- See [`M7_SPRINT_STATUS.md`](M7_SPRINT_STATUS.md) for detail

### Sprints 5–7 — Closeout & should-haves

- QA seed, ADR-0025 accepted, calendar/trend overlays, OLS confounder, heatmap cluster sort

### Sprint 9 — Spec complete (without sleep / cycle / LLM)

| Paket | Inhalt                                                              |
| ----- | ------------------------------------------------------------------- |
| A     | Entry drawer + symptom×tag detail sheet on `/insights`              |
| B     | Confounder UX in `InsightCard` + feed ranking                       |
| C     | Tag-heatmap cluster sort, a11y, E2E hooks                           |
| D     | Combined symptom+tag Jaccard in tag-clusters API                    |
| E     | Spec checkbox sign-off + docs                                       |

### Sprint 8 / post-M7 — Optional (foundations landed 2026-07-15)

- Ollama (#148), weekly digest (#147), changepoint (#149)
- CLI: `uv run --python 3.12 python -m app.workers.digest --once`
- API: `GET /api/v1/insights/digest/latest`
- Remaining: UnifiedPush/FCM delivery of digest (M4.2)

## Acceptance Criteria

### Core (Sprints 1–7) — done

- [x] Lasso and lag produce reproducible results on fixed input data
- [x] Symptom insights integrated in `/insights` feed per ADR-0025
- [x] `pgvector` migration applied; tag vectors recomputed nightly
- [x] Cluster cards use neutral copy (no "AI"/"ML" language)
- [x] `SymptomCalendarHeatmap` and `SymptomTrendOverlay` (Sprint 6)
- [x] Visual QA mock + seeded automated sign-off (Sprint 5)
- [x] CI green for M7 core

### Spec complete (Sprint 9) — done

- [x] Interaction: calendar/heatmap → entry drawer; symptom×tag detail sheet
- [x] Feed confounder mute + sort downgrade
- [x] Tag-cooccurrence heatmap cluster sort (`robust`)
- [x] Combined symptom+tag cluster API
- [x] Spec docs signed off ([`M7_SPRINT9_PLAN.md`](M7_SPRINT9_PLAN.md))

### Optional (Sprint 8 / post) — foundation

- [x] LLM optional and disableable without feature loss (#148)
- [x] Weekly digest snapshot API + worker (#147)
- [x] Changepoint detection in analytics pipeline (#149)
- [ ] Digest push notification delivery (blocked on M4.2)

## Prerequisites

- M3 insight engine shipped
- M5 co-occurrence heatmap / aggregation table
- Sprint-free pointbiserial Symptom↔Mood bugfix (ADR-0025 prerequisite)
- `pgvector` available on Synology NAS Docker image (verify before sprint)

## Deferred outside M7

| Topic              | Target                         |
| ------------------ | ------------------------------ |
| Sleep×Symptom      | M8                             |
| Cycle × lifestyle  | M7.1                           |
| Notes signals      | **Foundation shipped** (#201/#202); further polish under notes epic |
| Digest push        | M4.2                           |
