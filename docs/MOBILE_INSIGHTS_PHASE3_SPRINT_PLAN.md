# Mobile Insights Phase 3 — Closeout Sprint Plan

Last updated: 2026-06-26

Tracking document for the closeout of Phase 3 (`codex/mobile-insights-foundation`)
from [`docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](MOBILE_WEB_IMPLEMENTATION_PLAN.md).

## Context

Phase 3 code is fully implemented on branch `codex/mobile-insights-foundation`
(last commit: 2026-06-24). The three remaining gaps before merge are:

1. **Figma parity** — the `Mobile / Insights` frame (`28:615`) still reflects the
   pre-Sprint-3 composition; `MobileInsightLead` and the Sprint 3 hierarchy do
   not exist as Figma nodes yet.
2. **Rendered QA** — browser QA at 390 / 430 / 1280 px in light and dark is not
   yet signed off.
3. **PR + documentation closure** — branch not yet merged; `MOBILE_WEB_IMPLEMENTATION_PLAN.md`
   Phase 3 status is still "pending closeout"; `CHANGELOG.md` not updated.

Sprint discipline: execute in order. Sprint 1 (Figma) unblocks Sprint 2 (QA
sign-off against a stable reference). Sprint 3 (merge) runs only after QA is
green.

---

## Sprint Overview

| Sprint | Title             | Exit criterion                                          | Status  |
| ------ | ----------------- | ------------------------------------------------------- | ------- |
| 0      | Scope & Docs      | This document committed; ADR gap confirmed; node IDs noted | Pending |
| 1      | Figma Parity      | Sprint 3 Figma screen and MobileInsightLead component exist | Pending |
| 2      | Rendered QA       | QA signed off at 390 / 430 / 1280 px, light + dark     | Pending |
| 3      | PR & Closeout     | Branch merged; docs, changelog, issues closed           | Pending |

---

## Sprint 0 — Scope & Docs

**Goal:** Confirm scope, check for ADR gaps, note Figma node structure before
implementation begins. No code or design changes.

### ADR gap check

Existing ADRs cover all Phase 3 technical decisions:

- ADR-0017 — five-screen architecture and `< 768 px` mobile shell boundary
- ADR-0018 — `InsightCard` confidence visualisation (featured prop, `showConfidenceSummary`)
- ADR-0021 — insight maturity phases and `InsightStageHeader`
- ADR-0035 — temporal correspondence and divergent scale tokens

No new ADR is required for the ranking utility (`insightRanking.ts`):
`confidence × |effect_size|` is a deterministic sort, not a model or
architectural decision. If the ranking formula changes in a future milestone,
open an ADR at that point.

### Figma reference nodes (pre-Sprint-1)

| Node | Description | Status |
| ---- | ----------- | ------ |
| `28:615` | `Mobile / Insights` (old composition — DO NOT USE as Sprint 3 reference) | Outdated |
| `59:1293` | `Mobile / Trends / Summary` — structural reference for Lead layout | Use as pattern |
| `48:1089` | `Mobile / Entry / Quick Capture` — component composition reference | Use as pattern |
| Sprint 3 screen | To be created in Sprint 1 | Pending |
| `MobileInsightLead` component | To be created in Sprint 1 | Pending |

### Scope boundaries (unchanged from Phase 3 definition)

**In scope:**
- `MobileInsightLead` Figma component matching the Svelte implementation
- Sprint 3 mobile Insights screen frame (summary → TabBar → remaining feed)
- Empty, loading, and error states for the mobile lead area
- QA at 390, 430, 1280 px in light and dark

**Out of scope:**
- Offline retry state for Insights (no Dexie queue in this phase — consistent with ADR-0009)
- Co-occurrence heatmap on mobile (remains behind `<details>`, no mobile redesign)
- Analytics toggle redesign
- Any backend changes

---

## Sprint 1 — Figma Parity

**Goal:** Create the production-aligned Figma components and Sprint 3 screen so
that the QA sign-off in Sprint 2 can reference a stable design document.

### Deliverables

#### 1a — `MobileInsightLead` Figma component

Structure mirrors `MobileInsightLead.svelte` exactly:

```
MobileInsightLead (Auto Layout, vertical, gap: space-3)
  ├── Header block (Auto Layout, vertical, gap: space-1)
  │   ├── Eyebrow label  — token: color-text-muted, text-xs, weight 700, uppercase
  │   ├── h2             — text-xl, weight 700, line-height 1.25
  │   └── Context line   — color-text-muted, text-sm
  ├── InsightCard (featured=true, showConfidenceSummary=true)
  ├── Correlation note   — color-text-muted, text-sm + primary-colored link
  └── Maturity block (conditional, Auto Layout, vertical, gap: space-2)
      ├── Section label  — color-text-muted, text-xs, weight 700, uppercase
      └── InsightStageHeader instance
```

- Use existing `InsightCard`, `InsightStageHeader` components from the library.
- Expose component properties: `insight` (InsightCard variant), `showMaturity` (boolean).
- Bind token variables for all color and spacing values — no hard-coded hex.

#### 1b — Sprint 3 Mobile Insights screen frame

New top-level frame: `Mobile / Insights / Sprint 3` (width: 390).

Layout (top to bottom):
1. `ScreenHeader` instance — title "Erkenntnisse", subtitle "Stärkstes aktuelles Signal"
2. `MobileInsightLead` component (new, from 1a)
3. `TabBar` instance — options: "Erkenntnisse" (active) | "Matrix"
4. Section: "Weitere Muster" heading + `InsightFeed` (remaining cards, compact)
5. `AppNav` — Insights active

State variants to create:
- **Default** (lead card visible, maturity block shown, ≥1 remaining card)
- **Empty** (no insights yet — `InsightStageHeader` collecting phase placeholder)
- **Loading** (skeleton for lead area)
- **Matrix view** (TabBar switched to Matrix, `InsightMatrix` visible, no lead)

### Acceptance criteria

- [ ] `MobileInsightLead` component exists in Figma and matches Svelte structure
- [ ] Sprint 3 screen frame exists with correct hierarchy
- [ ] Empty, loading, and matrix states are designed
- [ ] All color values reference design tokens (no raw hex)
- [ ] Figma README updated with Sprint 3 node IDs
- [ ] `MOBILE_WEB_IMPLEMENTATION_PLAN.md` Figma note updated

---

## Sprint 2 — Rendered QA

**Goal:** Sign off browser QA against the branch at standard breakpoints in both
themes. All failures must be fixed before Sprint 3.

### QA matrix

| Viewport | Theme | MobileInsightLead | TabBar | Remaining feed | No H-scroll | Matrix view |
| -------- | ----- | ----------------- | ------ | -------------- | ----------- | ----------- |
| 390 × 844 | Light | [ ] | [ ] | [ ] | [ ] | [ ] |
| 390 × 844 | Dark  | [ ] | [ ] | [ ] | [ ] | [ ] |
| 430 × 932 | Light | [ ] | [ ] | [ ] | [ ] | [ ] |
| 430 × 932 | Dark  | [ ] | [ ] | [ ] | [ ] | [ ] |
| 1280 × 900 | Light | n/a (lead hidden) | [ ] | [ ] | [ ] | [ ] |
| 1280 × 900 | Dark  | n/a (lead hidden) | [ ] | [ ] | [ ] | [ ] |

### Dev Mode QA (activate via Settings > Developer)

All four maturity phases must render correctly in `MobileInsightLead`:

- [ ] `collecting` — no lead, `InsightStageHeader` fallback shown
- [ ] `early` — lead shown, maturity block visible
- [ ] `provisional` — lead shown, maturity block visible
- [ ] `robust` — lead shown, maturity block visible

### E2E smoke

Confirm the three existing Playwright tests pass on the branch:

- [ ] `390px prioritizes the strongest signal, confidence, and maturity`
- [ ] `430px keeps matrices and analytics behind explicit detail actions`
- [ ] `desktop preserves the existing analysis-first composition`

### Acceptance criteria

- [ ] All QA matrix rows signed off
- [ ] No horizontal scroll at any tested viewport
- [ ] Dev Mode maturity phase switching works as expected
- [ ] All three E2E tests pass
- [ ] QA results documented in `docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`

---

## Sprint 3 — PR & Closeout

**Goal:** Merge the branch, update all documentation, close or rescope GitHub
issues.

### Deliverables

- [ ] PR `codex/mobile-insights-foundation → main` opened and merged
  - PR description references Phase 3 exit criteria from `MOBILE_WEB_IMPLEMENTATION_PLAN.md`
  - Checklist: Figma parity (Sprint 1), QA sign-off (Sprint 2), E2E green
- [ ] `docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md` Phase 3 status → **complete**
  - Add Figma Sprint 3 node ID under Phase 3 verification section
- [ ] `apps/web/figma/README.md` updated with Sprint 3 screen node ID
- [ ] `CHANGELOG.md` updated under `Unreleased`:
  ```
  ### Mobile Insights (Phase 3)
  - Add MobileInsightLead component: strongest insight first on mobile viewports
  - Add deterministic insight ranking utility (confidence × |effect_size|)
  - Rank insights before mobile/desktop split in /insights route
  - Add mobile-specific i18n keys (insights.mobile.*)
  - Add Playwright E2E coverage for 390 px, 430 px, and 1280 px insight views
  ```
- [ ] GitHub issue `#200` — comment with rescope note:
  > Mobile note composer UX deferred. Phase 3 (Mobile Insights hierarchy) is
  > complete. Note markers on mobile remain a follow-up under M8 / Notes epic.
- [ ] CI — Web green on merge commit (`ci-web.yml`)

### Definition of Done

| Criterion | Evidence |
| --------- | -------- |
| Branch merged to `main` | GitHub merge commit |
| Figma Sprint 3 screen exists | Node ID in README |
| QA signed off | `docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md` |
| E2E green | CI `ci-web.yml` pass |
| `MOBILE_WEB_IMPLEMENTATION_PLAN.md` Phase 3 → complete | Updated file on `main` |
| `CHANGELOG.md` updated | Entry under Unreleased |
| Issue `#200` commented/rescoped | GitHub issue |
| No gamification violations | `noGamificationCopy.test.ts` passes |
