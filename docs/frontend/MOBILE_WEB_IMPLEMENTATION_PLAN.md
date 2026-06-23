# Mobile/Web Frontend Implementation Plan

**Status:** Sprint 0 and Phase 1 complete; Phase 2 is the next implementation slice.
**Default:** Resolve mobile topics first unless a conflict gate below fails.

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

## Phase 2: Mobile Trends

1. Define a mobile Trends summary contract: selected range, top metric movement,
   strongest tag/symptom signals, and an explicit detail action.
2. Reuse existing analytics outputs; do not calculate alternate mobile results.
3. Present full timeseries, heatmap, and comparison interactions in focused
   sheets or detail states where they remain usable.
4. Keep desktop `TrendsComparePanel`, charts, cursor linking, and heatmaps as
   the primary analytical composition.

**Exit:** Mobile provides an understandable summary and reachable detail without
rendering the desktop dashboard at reduced scale.

## Phase 3: Mobile Insights

1. Add Figma components for `InsightCard`, `InsightFeed`, maturity/quality,
   confidence, disclaimer, and empty/loading states.
2. Make mobile feed hierarchy explicit: strongest actionable insight first,
   maturity context second, deeper matrices and co-occurrence behind detail.
3. Keep correlation language non-causal and confidence visible.

**Exit:** Figma and code expose the same insight states and hierarchy on mobile.

## Phase 4: Supporting mobile flows

1. Add Settings essentials, tag/symptom management, auth/onboarding,
   verification, offline, install, update, and sync-retry screens.
2. Preserve desktop management density while sharing controls and validation.
3. Confirm privacy and health-data consent flows before Capacitor/Health Connect
   work.

**Exit:** No mobile-critical recovery or account flow remains undocumented.

## Phase 5: Desktop consolidation

1. Review each primary route above 768 px and replace accidental stretched
   mobile layouts with deliberate split views or wide analytical regions.
2. Keep Home restrained; prioritise desktop depth in Trends, Insights, and
   Settings.
3. Align Figma web screens with rendered code and remove obsolete mockups.

**Exit:** Desktop uses available space efficiently without changing route or
domain semantics.

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
