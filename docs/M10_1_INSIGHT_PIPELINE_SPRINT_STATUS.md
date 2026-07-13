# M10.1 Sprint Status — Insight-Pipeline, Trigger & Tag-Gruppen-Reifegrad

Last updated: 2026-07-13

Tracking document for [`M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md`](M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md).

## Overview

| Paket | Titel | Status |
| ----- | ----- | ------ |
| 0 | Freigabe & Doc-Baseline | Complete |
| A | Insight-Trigger (Backend) | Complete (#383) |
| B | Tag-Gruppen-Stufen | Complete (#383) |
| C | Wochentags-Dashboard & Home | Not started |
| D | Frontend Tag-Gruppen-Reifegrad | Complete (#384) |
| E | Docs, i18n, E2E, Quality Gate | Complete |

## Paket E — Checklist

- [x] E1 API.md
- [x] E2 PHASE_INSIGHT_MATRIX.md
- [x] E3 M9 thresholds addendum
- [x] E4 ADR-0016 + ADR-0021 cross-refs
- [x] E5 docs-site
- [x] E6 CHANGELOG
- [x] E7 E2E user-journeys (regenerate + tag groups badge)
- [x] E8 QA checklist sync
- [x] D6 Settings regenerate

## Remaining (Paket C)

- [ ] `weekday_summary` dashboard + HomeWeekdayOverview

## Verification

```bash
cd backend && uv run --python 3.12 pytest \
  tests/test_tag_clusters.py tests/test_insight_worker.py tests/test_insights.py -q
pnpm --filter @correlcore/web exec vitest run \
  src/lib/components/insights/TagGroupsSection.test.ts \
  src/routes/settings/page.test.ts \
  src/lib/api/insights.test.ts -q
```
