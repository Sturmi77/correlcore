# Mobile/Web Frontend Audit

**Date:** 2026-06-27 (closeout refresh; original 2026-06-22)  
**Direction:** Mobile daily use first; web analysis first  
**Figma:** [Audit overview](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=31-1089)

> **Canonical status snapshot:** [`FRONTEND_STATUS.md`](FRONTEND_STATUS.md) consolidates
> deploy readiness, test evidence, sprint ledger, and open tracks from this audit.

**Mobile closeout status:** Phases 0–4 are **complete** (code, Figma Sprint 1–4, cross-phase QA).
Sign-off: [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md).
**Production-grade design system:** Sprints E–G + I complete; Sprint H deferred — [`FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md).
Phase 5 desktop consolidation remains a separate track.

## Executive findings (post-closeout)

1. **Mobile Trends is resolved for daily use.** Sprint 2 delivers ranked summaries and
   explicit detail drill-down; desktop keeps the full comparison canvas (ADR-0035 adds
   shared daily axis, cursor, and strip mode on wide screens).
2. **Mobile Insights hierarchy is aligned.** Sprint 3 Figma (`98:1573`) and
   `MobileInsightLead` match the code contract; matrices and co-occurrence stay behind
   explicit detail actions.
3. **Entry mobile capture is production-ready.** Sprint 1 Figma and Playwright cover
   compact optional details, offline retry, touch targets, and read-only history.
4. **The 768 px shell split is stable.** Bottom nav below 768 px, side rail at and
   above; route-level desktop composition is the Phase 5 follow-up, not a mobile blocker.
5. **Supporting flows have Figma parity.** Sprint 4 (`105:1626`) covers Settings,
   symptoms, App & Offline, auth recovery, onboarding touch states, and PWA overlays.
6. **A separate mobile codebase is not justified.** Shared routes, stores, and analytics
   contracts hold through Phase 4.

## Remaining gaps (out of production-grade scope)

- **Code Connect library publish:** 20 local templates ready; live activation needs Figma Org **Dev or Full seat** (Sprint H). See [`FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md).
- **Entry desktop workspace:** wider layout polish — Phase 5.
- **Backend product gaps:** password recovery, reminders, account deletion.

**Closed in Sprint I (2026-06-27):** Production-grade QA doc, dark theme E2E smoke
(`mobile-theme-parity.spec.ts`), audit refresh, Figma overview board theme row.
Sign-off: [`docs/quality/FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md).

**Closed in Sprint E (2026-06-27):** Figma Light/Dark variable modes on
`CorrelCore / Color`, dark reference board `120:2096`, legacy frame deprecation
badges, Sprint 3 Default layout overflow fix.

**Closed in Sprint F (2026-06-27):** Sprint 5 Home flow `121:2292`, auth entry
B4b, tag management B1b, Insights matrix @ 430 px `121:2781`.

**Closed in Sprint G (2026-06-27):** Code Connect templates for InsightCard,
InsightStageHeader, InsightQualityMeter, TagChip, FormField, MobileTrendsSummary,
InsightMatrix; component sets `131:31`, `131:62`, `131:3914`; variant doc board
`131:3864`.

## Screen matrix

| Screen            | Mobile | Web    | Figma Sprint    | Primary note                                            |
| ----------------- | ------ | ------ | --------------- | ------------------------------------------------------- |
| Home / Today      | Green  | Green  | 5 `121:2292`    | Sprint 5 mobile Home flow; legacy `21:3` reference-only |
| Entry             | Green  | Yellow | 1 `48:1089`     | Mobile capture complete; desktop workspace TBD          |
| Trends            | Green  | Green  | 2 `59:1285`     | Mobile summary + detail; desktop full canvas            |
| Insights          | Green  | Green  | 3 `98:1573`     | Mobile lead + tabs; desktop analysis-first              |
| Settings          | Green  | Green  | 4 `105:1626`    | Stacked mobile management; dense desktop rows           |
| Auth / Onboarding | Green  | Yellow | 4 B4–B5 + F B4b | Login/register in F; verification in B4                 |
| Offline / PWA     | Green  | Green  | 4 B3/B6         | Lifecycle in code + Figma; Entry-owned retry            |

Legend: **Green** = mobile closeout signed off. **Yellow** = functional but not the
focus of Phases 0–4 or needs Phase 5 density work.

## Component findings

### Mobile-critical (closeout complete)

- `EntryForm`, `TagPicker`, `SymptomChecker`, `ScaleSlider`: Sprint 1 coverage + E2E.
- `MobileInsightLead`, `InsightFeed`, `InsightCard`, `InsightMatrix`: Sprint 3 code +
  Figma; matrix layer toggles added in M5.1 (#214 Finding 3).
- Settings, auth, onboarding, offline/PWA: Sprint 4 Figma + supporting-flows E2E.

### Web-primary (unchanged)

- `MetricTimeseries`, `ComparisonHeatmap`, `TrendsComparePanel`, `UnifiedStripChart`,
  `TagHeatmap`, `HabitsPanel` retain full analytical form on desktop.
- Mobile communicates top signals and opens focused details.

### Code Connect templates

Repository templates in [`apps/web/figma/components/`](../../apps/web/figma/components/)
(20 files). **Local contract complete** (Sprint G). Published-library activation
requires Figma Organization/Enterprise **Dev or Full seat** (Sprint H — deferred).

## Conflicts and constraints

- ADR-0017 five-screen architecture remains intact.
- Home stays a Daily Brief (M5 streamline amendment).
- Trends mobile = simplification, not dashboard compression.
- Capacitor reuses SvelteKit; no second frontend.
- Legacy `Mobile / Insights` frame `28:615` is not the Sprint 3 reference (`98:1573`).

## Evidence

- Machine-readable matrix:
  [`apps/web/figma/mobile-web-audit.json`](../../apps/web/figma/mobile-web-audit.json)
- Figma node ledger:
  [`apps/web/figma/correlcore-figma-map.json`](../../apps/web/figma/correlcore-figma-map.json)
- Cross-phase QA:
  [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md)
- Production-grade QA (Sprints E–G, I):
  [`docs/quality/FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md)
- Responsive breakpoint: `apps/web/src/app.css` at `@media (min-width: 768px)`.
