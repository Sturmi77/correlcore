# Mobile/Web Frontend Implementation Plan

**Status:** **Mobile closeout complete** — Phases 0–4 (code, Figma, QA). Phase 5
(desktop consolidation) is the next track. See
[`docs/MOBILE_CLOSEOUT_SPRINT_PLAN.md`](../MOBILE_CLOSEOUT_SPRINT_PLAN.md).

**Full frontend audit (2026-06-27):** [`FRONTEND_STATUS.md`](FRONTEND_STATUS.md).

**Default:** Resolve mobile topics first unless a conflict gate below fails.

## Current GitHub sprint ledger

**Completed on `main` @ `7b7ca8a` and closeout docs**

- Phases 0–4 mobile code paths (Entry, Trends, Insights hierarchy, supporting
  flows, PWA lifecycle).
- Phase 4 mobile supporting flows in code: Settings essentials, symptom
  management, App & Offline status, global PWA/update state, offline recovery
  messaging, and mobile touch refinements for onboarding/profile inputs.
- Review findings from recent mobile PRs addressed: UTC-based Entry editability,
  hydration-safe Entry compact mode, touch-enabled mobile Insights Playwright
  contexts, scoped Insight lead assertions, tolerant ranking float checks, no
  duplicate maturity badge in the lead card, valid Code Connect metadata order,
  a valid `ScaleSlider` snippet, and a real `MetricCard` implementation behind
  the Figma mapping.
- Shared contracts remain intact: no second mobile frontend, no alternate
  analytics path, no background health-data queue, and no route/API split for
  mobile.
- Phase 3 Figma: `MobileInsightLead` component and Sprint 3 screen states
  (Default, Empty, Loading, Matrix) — node `98:1573`.
- Phase 3 QA closeout: [`docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`](../quality/MOBILE_INSIGHTS_PHASE3_QA.md).
- Phase 4 Figma: Supporting flows Sprint 4 board — node `105:1626` (22 screens,
  1680 px layout board).
- Cross-phase mobile QA: [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md).
- Sprint D: audit refresh, `MobileInsightLead.figma.ts`, GitHub #200 / #214 closure.

**Still open**

- **Code Connect publish (Sprint H)** — Figma Dev/Full seat + library publish. Local
  templates complete (Sprint G). Track: [`FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](../FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md).
- Phase 5 desktop consolidation (wide-screen density, split views).
- Define backend/product contracts for password recovery, reminders, account
  deletion, and future health-data import consent/revocation.

**Production-grade design system (Sprints E–G, I):** signed off — see
[`docs/quality/FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md).

**Next recommended sprint**

**M9 — Beta Hardening** is the next main milestone after M5.1 UX polish closeout
(2026-07-10). See [`docs/M5_1_SPRINT_STATUS.md`](../M5_1_SPRINT_STATUS.md),
[`docs/M9_SPRINT_PLAN.md`](../M9_SPRINT_PLAN.md), and
[`docs/M9_SPRINT_STATUS.md`](../M9_SPRINT_STATUS.md) (Sprint 0 audit: 2026-07-11).

Sprint **H** (Figma Code Connect publish) remains optional when a Figma seat is
available; Phase 5 desktop consolidation can proceed in parallel.

**M5.1 — UX Polish & Flow Consolidation** is **complete** (2026-07-10). The
`ux(O-xx)` issues for onboarding, Home, Insights, Habits, and PWA polish were
delivered via GUI optimization Phases 1–3 and formally closed in
[`docs/M5_1_UX_POLISH_PLAN.md`](../M5_1_UX_POLISH_PLAN.md).

## Success criteria

- Daily entry is complete, accessible, recoverable, and usable at 390 px.
- Mobile Trends and Insights communicate useful information without compressed
  desktop charts.
- Desktop keeps analysis depth and management efficiency.
- Routes, API contracts, stores, validation, and domain calculations stay
  shared.
- Every affected screen covers loading, empty, error, partial, offline, and
  ready states where applicable.

## Conflict gates

Mobile work proceeds first unless it would:

1. change an API/domain contract used by desktop;
2. contradict ADR-0017's five-screen architecture;
3. duplicate analytics or validation logic by viewport;
4. introduce a second frontend codebase;
5. block the existing desktop flow without a migration path.

If a gate fails, extract or stabilise the shared contract first, then resume the
mobile slice. Visual or composition differences alone are not conflicts.

## Sprint 0: Shared surface foundation (complete)

1. Added one source of truth for the 768 px shell breakpoint, five baseline
   viewports, primary surface roles, and the six UI data states.
2. Extended `DataState` with a `partial` state while preserving rendered content.
3. Added route contracts for root shell ownership and navigation parity.
4. Added browser coverage for shell placement, horizontal overflow, and 44 px
   navigation targets at 390, 430, 768, 1280, and 1440 px.
5. Added the editable Figma contract board:
   https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=36-1089

**Verification:** 11 unit/contract tests, five Playwright viewport tests, and
`svelte-check` with zero errors and zero warnings.

## Phase 1: Mobile entry foundation (complete)

1. Added the complete mobile Entry flow in Figma: quick capture, optional
   details, validation, saving/saved, explicit offline retry, tag limits,
   custom tags, symptom disclosure, and read-only history.
2. Added implementation coverage for `SymptomChecker`, `TagPicker`, save
   status, optional-detail disclosure, and mobile Entry composition.
3. Kept shared entry data and validation in `EntryForm` while making mobile
   composition responsive below the shared 768 px breakpoint.
4. Added automated coverage at 390 x 844 and 430 x 932, including 44 px touch
   targets, overflow, offline retry, desktop parity, and the seven-day boundary.

Offline edits deliberately remain visible and retryable instead of being
silently queued. A durable pending-sync queue is a separate product and data
architecture decision under ADR-0009 and ADR-0013.

**Exit:** A user can complete, recover, and understand a daily entry in at most
60 seconds without desktop regressions.

**Verification:** 9 focused unit tests, five Playwright Entry scenarios,
`svelte-check` with zero errors and warnings, and the editable Figma flow:
https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=48-1089

## Phase 2: Mobile Trends (complete)

1. Added a mobile Trends summary contract for the selected range, strongest
   metric movement, most frequent tag, and most reported symptom.
2. Reused the existing timeseries, tag heatmap, and symptom heatmap responses;
   mobile performs no alternate analytics calculation.
3. Put the full timeseries, heatmap, filters, sorting, cursor, and comparison
   interactions behind an explicit mobile detail action.
4. Kept desktop `TrendsComparePanel`, filters, charts, cursor linking, and
   heatmaps permanently visible as the primary analytical composition.

**Exit:** Mobile provides an understandable summary and reachable detail without
rendering the desktop dashboard at reduced scale.

**Verification:** Eight new focused unit and route tests, four Playwright
summary/detail/empty/desktop scenarios, `svelte-check`, and the editable Figma
flow:
https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=59-1285

## Phase 3: Mobile Insights

1. Add Figma components for `InsightCard`, `InsightFeed`, maturity/quality,
   confidence, disclaimer, and empty/loading states.
2. Make mobile feed hierarchy explicit: strongest actionable insight first,
   maturity context second, deeper matrices and co-occurrence behind detail.
3. Keep correlation language non-causal and confidence visible.

**Exit:** Figma and code expose the same insight states and hierarchy on mobile.

**Implemented in code:** The mobile findings view now ranks insights through a
shared deterministic utility and presents the strongest signal first with a
visible semantic confidence scale. Maturity context follows the lead signal,
remaining patterns keep the existing filters, and matrix/co-occurrence surfaces
remain behind explicit detail controls. Desktop keeps the existing analysis
composition and API contract.

**Figma (complete 2026-06-26):**

- Component: `MobileInsightLead` — https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1541
- Flow: `Mobile Insights / Sprint 3 Flow` — https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1573

**QA (complete 2026-06-26):** Rendered sign-off at 390, 430, and 1280 px documented in
[`docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`](../quality/MOBILE_INSIGHTS_PHASE3_QA.md).
Playwright: `mobile-insights-foundation.spec.ts`, `m7-insights-mobile.spec.ts`.

## Phase 4: Supporting mobile flows

1. Add Settings essentials, tag/symptom management, auth/onboarding,
   verification, offline, install, update, and sync-retry screens.
2. Preserve desktop management density while sharing controls and validation.
3. Confirm privacy and health-data consent flows before Capacitor/Health Connect
   work.

**Exit:** No mobile-critical recovery or account flow remains undocumented.

**Implemented in code:** Settings now links to shared tag and symptom
management plus an App & Offline status screen. Custom symptoms can be renamed
or deleted with explicit confirmation while curated defaults remain read-only.
A shared PWA lifecycle store exposes connection loss, waiting service-worker
updates, install state, update checks, and restart activation to the app shell,
offline recovery screen, and settings. Retrospective and profile onboarding
now keep 44 px touch targets and stack actions at mobile widths. Unsaved health
data remains visible on the originating Entry screen and requires explicit
retry; there is no silent background sync queue.

**Documented dependencies:** Password recovery still needs a backend contract
before a route can be implemented. Reminders and account deletion remain
explicit product/backend backlog. Health-data import and Capacitor work remain
gated on a dedicated consent and revocation flow.

**Figma (complete 2026-06-26):**

- Flow: [`Mobile Supporting Flows / Sprint 4 Flow`](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1626) — Settings, symptom management, App & Offline, auth recovery, onboarding, PWA overlays.

**QA (complete 2026-06-27):** Cross-phase sign-off in
[`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md).
Playwright: `mobile-supporting-flows.spec.ts` (17/17 mobile E2E suite @ `d77b556`).

## Phase 5: Desktop consolidation

1. Review each primary route above 768 px and replace accidental stretched
   mobile layouts with deliberate split views or wide analytical regions.
2. Keep Home restrained; prioritise desktop depth in Trends, Insights, and
   Settings.
3. Align Figma web screens with rendered code and remove obsolete mockups.

**Exit:** Desktop uses available space efficiently without changing route or
domain semantics.

**Out of scope** for the mobile closeout plan. Resume after Phases 0–4 mobile
parity is signed off in QA.

## Verification and rollout

- Component tests cover new variants and state transitions.
- Route tests assert shared shell/navigation and state primitives.
- Browser QA covers 390, 430, 768, 1280, and 1440 px.
- E2E covers entry save/offline retry, Trends summary-to-detail, Insights
  disclosure, auth verification, and settings management.
- Accessibility checks cover keyboard, focus order, labels, contrast, reduced
  motion, and non-colour chart differentiation.
- Deliver phases as separate reviewable PRs; do not combine Entry, Trends, and
  Insights redesigns into one rollout.
