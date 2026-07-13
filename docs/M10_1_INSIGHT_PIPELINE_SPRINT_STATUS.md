# M10.1 Sprint Status — Insight-Pipeline, Trigger & Tag-Gruppen-Reifegrad

Last updated: 2026-07-13

Tracking document for [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md).

**Prerequisite:** Freigabe [`INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md`](proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md) + ADR-0037 Accepted.

## Overview

| Paket | Titel | Status |
| ----- | ----- | ------ |
| 0 | Freigabe & Doc-Baseline | In progress (Proposal PR #382) |
| A | Insight-Trigger (Backend) | Not started |
| B | Tag-Gruppen-Stufen | Not started |
| C | Wochentags-Dashboard & Home | Not started |
| D | Frontend Tag-Gruppen-Reifegrad | Not started |
| E | Docs, i18n, E2E, Quality Gate | Not started |

## Acceptance-criteria audit matrix

| Criterion | Paket | Code anchor | Test evidence | Gap |
| --------- | ----- | ----------- | ------------- | --- |
| `POST /insights/regenerate` | A | — | — | Not implemented |
| Post-batch insight trigger | A | — | — | Not implemented |
| Tag-Gruppen ab 30 Tagen (pair) | B | `tag_cluster_service.py` | `test_tag_clusters.py` | 90-day hard gate |
| Tag-Gruppen provisional ab 45 | B | — | — | Not implemented |
| `weekday_summary` Dashboard | C | `dashboard_service.py` | — | Not implemented |
| Home Weekday ohne `weekday_pattern` | C | `HomeWeekdayOverview` | — | Insight-only today |
| `cluster_maturity` UI | D | `TagGroupsSection` | — | Not implemented |
| ADR-0037 Accepted | 0 | `docs/adr/0037-*.md` | — | Vorgeschlagen |
| API.md / PHASE_MATRIX updated | E | docs | — | Pending |

## Sprint 0 — Checklist

- [x] [`INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md`](proposals/INSIGHT_PIPELINE_TAG_GROUPS_PROPOSAL.md) erstellt
- [x] [ADR-0037](adr/0037-insight-triggers-tag-cluster-maturity.md) Entwurf
- [x] [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md) erstellt
- [x] ARCHITECTURE.md §6 Verweis
- [ ] Proposal PR #382 merged
- [ ] ADR-0037 → Accepted
- [ ] GitHub-Milestone / Label `m10.1-insight-pipeline`

## Paket A — Checklist

- [ ] A1–A8 implementiert
- [ ] pytest insight worker + insights
- [ ] AGENTS.md Worker-Doku

## Paket B — Checklist

- [ ] B1–B9 implementiert
- [ ] 67-Tage-Regression grün
- [ ] ML 90d Regression grün

## Paket C — Checklist

- [ ] C1–C6 implementiert
- [ ] HomeWeekdayOverview Tests grün

## Paket D — Checklist

- [ ] D1–D5 implementiert
- [ ] i18n DE/EN

## Paket E — Checklist

- [ ] Proposal §7 Impact-Matrix abgearbeitet
- [ ] `M10_1_INSIGHT_PIPELINE_QA.md`
- [ ] CHANGELOG M10.1
- [ ] E2E user-journeys

## Baseline verification (pre-implementation)

```bash
cd backend && uv run --python 3.12 pytest tests/test_tag_clusters.py -q
# test_tag_clusters_return_insufficient_data_below_entry_threshold — expects 90 gate
```
