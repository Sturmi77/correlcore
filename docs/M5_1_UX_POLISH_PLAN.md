# M5.1 — UX Polish & Flow Consolidation Plan

Last updated: 2026-07-10

**Scope:** Consolidate the open UX topics tracked as `ux(O-xx)` issues into a
single intermediate milestone **M5.1** between Habits core (M5) and Beta Hardening
(M9). No new major backend domains; the focus is on flows, information architecture,
and polish over already-implemented functionality.

Canonical references:

- [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md) — updated M4/M4.1/M5/M5.1/M9 sections.
- [`frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md) — mobile closeout status.
- [`MOBILE_CLOSEOUT_SPRINT_PLAN.md`](MOBILE_CLOSEOUT_SPRINT_PLAN.md) — Phases 0–4 complete.
- [`frontend/O-20_PASSWORD_RESET_PLAN.md`](frontend/O-20_PASSWORD_RESET_PLAN.md) — out-of-scope backend dependency (#272).
- Open UX issues (`ux(O-xx)`): #251–#273 cluster.

---

## 1. Objectives

1. Make onboarding → first entry → first insight feel coherent and directed.
2. Align Home, Insights, and Habits so they present a clear next step depending on
   data maturity.
3. Ensure mobile PWA behaviours (install prompt, offline, export) feel natural and
   non-intrusive.
4. Prepare desktop analysis views for Beta by consolidating range and surfaces.

M5.1 is explicitly **pre-M9** and should complete before Beta testers are invited.

---

## 2. Issue Ledger

### 2.1 Onboarding & Entry bridge

- #251 — `ux(O-02): Open EntrySheet after onboarding complete`
- #260 — `ux(O-06): Integrate tag selection into first entry`
- #261 — `ux(O-07): Auto-login after email verification`
- #263 — `ux(O-09): Habit hint in onboarding tag step`

**Exit:** A new user completes onboarding and lands directly in a ready-to-use
entry surface with tag/habit context and no redundant login loops.

### 2.2 Home & Insights UX

- #252 — `ux(O-03): Insights empty-state CTA opens entry directly`
- #254 — `ux(O-05): Hide Home sparkline until sufficient data`
- #264 — `ux(O-12): Home Daily Brief brief-first layout`
- #266 — `ux(O-13): Home bridge for weekly analysis review`
- #268 — `ux(O-14): Gate Insights matrix and co-occurrence by maturity`

**Exit:** Home and Insights communicate data readiness and maturity states clearly,
and early stages guide users toward adding entries instead of showing empty or
overloaded analytics.

### 2.3 Entry & Habits surfaces

- #262 — `ux(O-08): Unify desktop entry surface`
- #265 — `ux(O-16): Inline habit setup on empty Habits panel`
- #267 — `ux(O-17): Heatmap drill-down via EntryHistorySheet`

**Exit:** Entry and Habits surfaces share a coherent visual language and drill-down
path. Heatmaps and habit panels allow setup and exploration without feeling
detached from daily entries.

### 2.4 PWA & Settings polish

- #269 — `ux(O-18): Defer PWA install banner until after first entry`
- #270 — `ux(O-19): Improve export discoverability in Settings`
- #273 — `ux(O-11): Check-email mobile mail-app deep link`

**Exit:** The PWA install prompt appears after the first meaningful entry, exports
are discoverable in Settings, and email verification flows link into the device
mail app smoothly.

### 2.5 Desktop analysis polish

- #271 — `ux(O-15): Trends global sticky range control (desktop)`

**Exit:** Desktop Trends provide a stable, global range control that supports
extended analysis without constant reset.

### 2.6 Out-of-scope UX issues

- #272 — `ux(O-20): Password reset UI (blocked on backend)`
  → Tracked separately in
  [`frontend/O-20_PASSWORD_RESET_PLAN.md`](frontend/O-20_PASSWORD_RESET_PLAN.md)
  and scheduled alongside backend work; not required for M5.1 exit.

---

## 3. Milestone Exit Criteria

M5.1 is **Done** when:

- [ ] All in-scope UX issues are closed or explicitly deferred to a post-v1.0
      polish track with rationale.
- [ ] Onboarding, Home, Entry, Insights, and Habits flows can be traversed
      end-to-end on mobile (390/430 px) and desktop (1280+ px) without dead ends or
      confusing detours.
- [ ] PWA install, export, and email verification flows feel contextual and are
      covered by minimal E2E tests.
- [ ] The design document and frontend implementation plan both reflect M5.1 as
      completed and M9 as the next main milestone.

---

## 4. Relation to M9 — Beta Hardening

Once M5.1 is complete, the product is feature-complete for the planned MVP (daily
entry, trends, Habits, Insights v1 + maturity, offline-first sync, mobile
closeout). M9 then focuses exclusively on:

- Monitoring and error tracking (GlitchTip).
- Backup/restore documentation and tests.
- Beta tester onboarding and feedback loops.
- Legal and privacy documentation before public selfhost (M10).

M5.1 must not introduce new backend health-data integrations or change core domain
contracts; it prepares the UX so Beta testers experience the intended flows instead
of raw scaffolding.
