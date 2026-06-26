# Mobile Insights Phase 3 — Closeout Sprint Plan

Last updated: 2026-06-26

Tracking document for the closeout of Phase 3 (Mobile Insights hierarchy) from
[`docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md).

Parent plan: [`docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md`](MOBILE_CLOSEOUT_SPRINT_PLAN.md).

## Context

Phase 3 code is on `main` (`MobileInsightLead`, `insightRanking`, `/insights`
route updates, E2E tests, i18n). Remaining closeout work is Figma parity sign-off,
rendered Browser QA, and documentation/GitHub closure.

Sprint discipline: execute in order. Sprint 1 (Figma) unblocks Sprint 2 (QA
sign-off against a stable reference). Sprint 3 (docs/closeout) runs after QA is
green.

---

## Sprint Overview

| Sprint | Title         | Exit criterion                                                | Status  |
| ------ | ------------- | ------------------------------------------------------------- | ------- |
| 0      | Scope & Docs  | This document committed; ADR gap confirmed; node IDs noted    | ✅ Done |
| 1      | Figma Parity  | Sprint 3 Figma screen and `MobileInsightLead` component exist | ✅ Done |
| 2      | Rendered QA   | QA signed off at 390 / 430 / 1280 px, light + dark            | ✅ Done |
| 3      | PR & Closeout | Docs updated, changelog, issue #200 rescoped                  | ✅ Done |

---

## Sprint 0 — Scope & Docs ✅

ADR gap check: no new ADR required. Covered by ADR-0017, ADR-0018, ADR-0021,
ADR-0035. Ranking utility is deterministic sort only.

---

## Sprint 1 — Figma Parity ✅

**Completed 2026-06-26** in Figma file
[CorrelCore Design System](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS).

### Created nodes

| Node      | Name                                     | URL                                                                 |
| --------- | ---------------------------------------- | ------------------------------------------------------------------- |
| `98:1541` | `MobileInsightLead` component            | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1541 |
| `98:1573` | `Mobile Insights / Sprint 3 Flow`        | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1573 |
| `98:1579` | `Mobile / Insights / Sprint 3 / Default` | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1579 |
| `99:1505` | `Mobile / Insights / Sprint 3 / Empty`   | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1505 |
| `99:1554` | `Mobile / Insights / Sprint 3 / Loading` | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1554 |
| `99:1607` | `Mobile / Insights / Sprint 3 / Matrix`  | https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=99-1607 |

### Structure

`MobileInsightLead` mirrors `MobileInsightLead.svelte`:

- Header block (eyebrow, h2, context line)
- `InsightCard` instance (`State=Ready`)
- Correlation note with primary link
- Maturity block with `InsightStageHeader` (`Phase=Robust`)
- Boolean component property `Show maturity`

Sprint 3 screens use `ScreenHeader`, `TabBar`, `Panel`, `AppNav`, and design-token
bindings (`color/text-muted`, `color/primary`, `spacing/*`).

**Do not use** legacy `Mobile / Insights` frame (`28:615`) as the Sprint 3
reference.

### Acceptance criteria

- [x] `MobileInsightLead` component exists and matches Svelte structure
- [x] Sprint 3 screen frame exists with correct hierarchy
- [x] Empty, loading, and matrix states are designed
- [x] Color values reference design tokens (no raw hex in new nodes)
- [x] Figma README and map updated with Sprint 3 node IDs
- [x] `MOBILE_WEB_IMPLEMENTATION_PLAN.md` Figma note updated

---

## Sprint 2 — Rendered QA ✅

**Completed 2026-06-26.** See [`docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`](quality/MOBILE_INSIGHTS_PHASE3_QA.md).

**Goal:** Sign off browser QA at standard breakpoints in both themes.

### QA matrix

| Viewport   | Theme | MobileInsightLead | TabBar | Remaining feed | No H-scroll | Matrix view |
| ---------- | ----- | ----------------- | ------ | -------------- | ----------- | ----------- |
| 390 × 844  | Light | [x]               | [x]    | [x]            | [x]         | [x]         |
| 390 × 844  | Dark  | [x]               | [x]    | [x]            | [x]         | [x]         |
| 430 × 932  | Light | [x]               | [x]    | [x]            | [x]         | [x]         |
| 430 × 932  | Dark  | [x]               | [x]    | [x]            | [x]         | [x]         |
| 1280 × 900 | Light | n/a               | [x]    | [x]            | [x]         | [x]         |
| 1280 × 900 | Dark  | n/a               | [x]    | [x]            | [x]         | [x]         |

### Dev Mode QA

- [x] `collecting` — no lead, `InsightStageHeader` fallback shown
- [x] `early_patterns` — lead shown, maturity block visible
- [x] `provisional` — lead shown, maturity block visible
- [x] `robust` — lead shown, maturity block visible

### E2E smoke

- [x] `390px prioritizes the strongest signal, confidence, and maturity`
- [x] `430px keeps matrices and analytics behind explicit detail actions`
- [x] `desktop preserves the existing analysis-first composition`

Document results in `docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`.

---

## Sprint 3 — PR & Closeout ✅

- [x] Mark Phase 3 **complete** in `MOBILE_WEB_IMPLEMENTATION_PLAN.md`
- [x] `CHANGELOG.md` entry under Unreleased (Mobile Insights Phase 3)
- [x] GitHub issue `#200` — rescope comment (note composer → M8 / Notes epic)
- [x] CI — Web green on `main` @ `7b7ca8a`
