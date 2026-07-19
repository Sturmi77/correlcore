# Completed milestones (archive)

**Archived:** 2026-07-19  
**Baseline:** Public selfhost release line **`1.0.x`** (first tag `v1.0.0` on 2026-07-11; latest patch `v1.0.6`; in-repo manifests/i18n/export aligned to `1.0.6`).

This file preserves the closed roadmap items that used to live in the root
[`README.md`](../../README.md). Active work stays in the README; details live in
the linked sprint / quality docs.

| Milestone | Closed        | Notes                                                                                                                                                                                                                                           |
| --------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M0**    | ✅            | Monorepo, CI/CD, Docker stack, native JWT auth, empty app shell                                                                                                                                                                                 |
| **M1**    | ✅            | Daily entry (mood, energy, stress, tags, symptoms, notes), Fernet at rest, login/register, email verification, GDPR erasure. Offline sync deferred → M4.1 ([ADR-0009](../adr/0009-offline-sync-nach-m4.md))                                     |
| **M2**    | ✅            | Mood time series, tag heatmap + drilldown, streaks, CSV/JSON export, custom SVG charts, habit schema prep ([ADR-0012](../adr/0012-m2-m5-streak-semantik.md)), developer view ([ADR-0015](../adr/0015-developer-view-version-identifikation.md)) |
| **M3**    | ✅            | Insights v1: correlations, template statements, confidence tiers, cold-start UX. [`M3_SPRINT_STATUS.md`](../M3_SPRINT_STATUS.md)                                                                                                                |
| **M3.1**  | ✅            | InsightStore, InsightCard/feed, disclaimer, neutral heatmap. [`M3.1_SPRINT_STATUS.md`](../M3.1_SPRINT_STATUS.md)                                                                                                                                |
| **M3.5**  | ✅ 2026-05-27 | Frontend web/mobile optimisation. [`M3_5_SPRINT_STATUS.md`](../M3_5_SPRINT_STATUS.md), [`quality/M3_5_VISUAL_QA.md`](../quality/M3_5_VISUAL_QA.md)                                                                                              |
| **M3.6**  | ✅ 2026-05-27 | Insight maturity phases (ADR-0021). [`M3_6_SPRINT_STATUS.md`](../M3_6_SPRINT_STATUS.md), [`quality/M3_6_VISUAL_QA.md`](../quality/M3_6_VISUAL_QA.md)                                                                                            |
| **M3.7**  | ✅ 2026-05-28 | Color system hardening, contrast gate. [`M3_7_SPRINT_STATUS.md`](../M3_7_SPRINT_STATUS.md)                                                                                                                                                      |
| **M4**    | ✅ 2026-06-30 | Entry slots, cycle day, guided onboarding, PWA shell + `/offline`. [`M4_SPRINT_STATUS.md`](../M4_SPRINT_STATUS.md)                                                                                                                              |
| **M4.1**  | ✅ 2026-06-30 | Dexie offline sync, push/pull, LWW, conflict log (feature-flagged). Closes #10, #24. [`M4.1_SPRINT_STATUS.md`](../M4.1_SPRINT_STATUS.md)                                                                                                        |
| **M5**    | ✅ 2026-06-30 | Habits Core (`build`/`reduce`). [`M5_SPRINT_STATUS.md`](../M5_SPRINT_STATUS.md)                                                                                                                                                                 |
| **M5.1**  | ✅ 2026-07-10 | UX polish & flow consolidation (#251–#273). [`M5_1_SPRINT_STATUS.md`](../M5_1_SPRINT_STATUS.md)                                                                                                                                                 |
| **M7**    | ✅ 2026-06-30 | Insights v2: Lasso, lag, symptoms, clustering; digest/Ollama/changepoint foundations (#147–#149). [`M7_SPRINT_STATUS.md`](../M7_SPRINT_STATUS.md)                                                                                               |
| **M9**    | ✅ 2026-07-11 | Beta hardening: monitoring, GlitchTip, GDPR self-service, backup/install docs, security CI. Closes #29. [`M9_SPRINT_STATUS.md`](../M9_SPRINT_STATUS.md)                                                                                         |
| **M10**   | ✅ 2026-07-11 | Public selfhost **v1.0**. Tag `v1.0.0`; patch line `v1.0.1`–`v1.0.6` (Android sideload hardening). [`M10_SPRINT_STATUS.md`](../M10_SPRINT_STATUS.md), [`CHANGELOG.md`](../../CHANGELOG.md#100--public-selfhost-release--2026-07-11)             |
| **M10.1** | ✅            | Insight triggers (ADR-0037), tiered tag clusters, Settings “Refresh insights”                                                                                                                                                                   |

**Not archived (still open):** M8 (Sleep & Health Connect), M11 (Play Store exit — engineering sprints 1–5 shipped), M12 (SaaS), M13 (Photo & media / MinIO).

See also: [`RELEASE_1_0_X_DOC_SYNC.md`](RELEASE_1_0_X_DOC_SYNC.md) for remaining doc/version sync work.
