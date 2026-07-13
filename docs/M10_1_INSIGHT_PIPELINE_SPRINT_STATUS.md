# M10.1 Sprint Status — Insight-Pipeline, Trigger & Tag-Gruppen-Reifegrad

Last updated: 2026-07-13

Tracking document for [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md).

**Prerequisite:** Freigabe [`INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md`](proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md) + ADR-0037 Accepted.

## Overview

| Paket | Titel | Status |
| ----- | ----- | ------ |
| 0 | Freigabe & Doc-Baseline | Complete (PR #382, ADR-0037 Accepted) |
| A | Insight-Trigger (Backend) | Complete (PR A+B) |
| B | Tag-Gruppen-Stufen | Complete (PR A+B) |
| C | Wochentags-Dashboard & Home | Complete (PR A+B+C) |
| D | Frontend Tag-Gruppen-Reifegrad | Not started |
| E | Docs, i18n, E2E, Quality Gate | Not started |

## Acceptance-criteria audit matrix

| Criterion | Paket | Code anchor | Test evidence | Gap |
| --------- | ----- | ----------- | ------------- | --- |
| `POST /insights/regenerate` | A | `endpoints/insights.py` | `test_insights.py` | — |
| Post-batch insight trigger | A | `endpoints/entries.py` | — | Integration test optional |
| Admin `POST /insights/trigger` | A | `endpoints/insights.py` | — | Manual / admin env |
| Tag-Gruppen ab 30 Tagen (pair) | B | `tag_cluster_service.py` | `test_tag_clusters.py` | — |
| Tag-Gruppen provisional ab 45 | B | `tag_cluster_service.py` | `test_tag_clusters.py` | — |
| `weekday_summary` Dashboard | C | `dashboard_service.py` | `test_dashboard.py` | — |
| Home Weekday ohne `weekday_pattern` | C | `HomeWeekdayOverview` | `homeWeekdayOverview.test.ts` | — |
| `cluster_maturity` UI | D | `TagGroupsSection` | — | Not implemented |
| ADR-0037 Accepted | 0 | `docs/adr/0037-*.md` | — | Done |
| API.md / PHASE_MATRIX updated | E | docs | — | Pending |

## Sprint 0 — Checklist

- [x] [`INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md`](proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md) erstellt
- [x] [ADR-0037](adr/0037-insight-triggers-tag-cluster-maturity.md) Entwurf
- [x] [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md) erstellt
- [x] ARCHITECTURE.md §6 Verweis
- [x] Proposal PR #382 merged
- [x] ADR-0037 → Accepted
- [ ] GitHub-Milestone / Label `m10.1-insight-pipeline`

## Paket A — Checklist

- [x] A1–A8 implementiert
- [x] pytest insight worker + insights
- [x] AGENTS.md Worker-Doku

## Paket B — Checklist

- [x] B1–B9 implementiert
- [x] 67-Tage-Regression grün
- [ ] ML 90d Regression grün (unchanged thresholds; run full pytest in CI)

## Paket C — Checklist

- [x] C1–C6 implementiert
- [x] HomeWeekdayOverview Tests grün

## Paket D — Checklist

- [ ] D1–D5 implementiert
- [ ] i18n DE/EN

## Paket E — Checklist

- [ ] Proposal §7 Impact-Matrix abgearbeitet
- [ ] `M10_1_INSIGHT_PIPELINE_QA.md`
- [ ] CHANGELOG M10.1
- [ ] E2E user-journeys

## Verification (Paket A+B+C)

```bash
cd backend && uv run --python 3.12 pytest tests/test_tag_clusters.py tests/test_insight_worker.py tests/test_insights.py tests/test_dashboard.py -q
pnpm --filter @correlcore/web exec vitest run src/lib/utils/homeWeekdayOverview.test.ts src/lib/components/home/HomeWeekdayOverview.test.ts
```
