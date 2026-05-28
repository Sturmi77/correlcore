# M8 Notes — Pattern Recognition & Clustering

Last updated: 2026-05-28

This document captures the scope and acceptance criteria for the
pattern recognition and clustering feature deferred from M4.

## Context

M3.x insight engine delivers correlation-based insights (tag ↔ metric
correlations). M5 delivers a raw co-occurrence heatmap. M8 adds
algorithmic pattern detection: automatic grouping of tags that tend to
co-occur, and surface-level anomaly detection.

Deferred to M8 because:

1. Requires a statistically robust data volume (≥ 90 days, ≥ 5 active tags)
2. `pgvector` extension must be available on the target deployment
3. Results must be explainable — no black-box outputs

## Scope

### Sprint 1 — pgvector Setup & Tag Embeddings

- Enable `pgvector` extension in Alembic migration
- Compute per-tag co-occurrence vectors from the aggregation table
  introduced in M5
- Store vectors in `tag_vectors` table
  (`tag_id`, `vector VECTOR(n)`, `computed_at`)
- Nightly background job recomputes vectors when new entries exist
- `docs/ARCHITECTURE.md` updated with pgvector dependency note

### Sprint 2 — Cluster Detection

- k-means clustering (k=3..6, elbow method) on tag vectors
- Clusters stored in `tag_clusters` table
  (`cluster_id`, `tag_id`, `label TEXT NULL`)
- `GET /api/v1/insights/tag-clusters` returns clusters with member tags
  and a human-readable label (generated from most-common tag names in
  cluster; no LLM required)
- Minimum data guard: endpoint returns `{ "status": "insufficient_data" }`
  when fewer than 90 day-entries or fewer than 5 active tags exist
- Unit tests: cluster count bounds, insufficient-data guard

### Sprint 3 — Frontend: Cluster Visualisation

- New section in Insights: "Tag Groups"
- Each cluster shown as a card with member tag chips and a generated
  label (e.g. "Work & Focus" if `work`, `focus`, `deadline` cluster)
- Tapping a cluster opens the co-occurrence heatmap (M5) filtered to
  that cluster's tags
- Insufficient-data empty state with tracking-consistency copy
- i18n keys `insights.clusters.*`
- Component tests

## Acceptance Criteria

- [ ] `pgvector` extension present and migration applied
- [ ] Tag vectors recomputed nightly
- [ ] `GET /api/v1/insights/tag-clusters` returns correct clusters
- [ ] Insufficient-data guard returns correct status
- [ ] Cluster cards render with member tags and label
- [ ] No "AI" or "machine learning" language in visible copy
- [ ] Copy uses: "Tags that often appear together"
- [ ] Visual QA at 375 px, 768 px, 1280 px (light + dark)
- [ ] CI green

## Prerequisites

- M5 co-occurrence heatmap shipped (provides aggregation table)
- `pgvector` available on Synology NAS Docker deployment
  (verify `pgvector` image tag before sprint start)
- ≥ 90 days of entry data in staging for manual QA

## Copy Guardrails

- Never use: "AI", "machine learning", "predicts", "detects"
- Use instead: "Tags that often appear together", "Recurring pattern",
  "Frequently co-occurring"
- All cluster labels derived from tag names — no synthetic copy
