# Mobile Closeout Sprint Plan

Last updated: 2026-06-26

**Scope:** Complete Code, Figma, and Documentation parity for the Mobile/Web
Implementation Plan through Phase 4. **Desktop consolidation (Phase 5) is out of
scope** for this plan.

Canonical references:

- [`docs/frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md)
- [`docs/frontend/MOBILE_WEB_AUDIT.md`](frontend/MOBILE_WEB_AUDIT.md)
- [`apps/web/figma/README.md`](../apps/web/figma/README.md)
- Figma: [CorrelCore Design System](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS)

---

## Executive summary

| Layer       | Phases 0–2 | Phase 3 Insights | Phase 4 Supporting | Overall |
| ----------- | ---------- | ---------------- | ------------------ | ------- |
| **Code**    | ✅         | ✅               | ✅                 | ✅      |
| **Figma**   | ✅         | ✅ (2026-06-26)  | ✅ (2026-06-26)    | ✅      |
| **Docs/QA** | ✅         | ✅               | ✅                 | ✅      |

**Mobile closeout (Phases 0–4) is complete.**

**Next tracks:**

1. **Production-grade design system** — [`FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md) (Sprints E–I: dark/light Figma, missing screens, Code Connect publish)
2. **Phase 5 desktop consolidation** — wide-screen density (separate plan)

---

## Phase ledger (mobile only)

| Phase | Title                 | Code | Figma | QA / Docs | Closeout doc                                                                     |
| ----- | --------------------- | ---- | ----- | --------- | -------------------------------------------------------------------------------- |
| 0     | Surface foundation    | ✅   | ✅    | ✅        | Sprint 0 board `36:1089`                                                         |
| 1     | Mobile Entry          | ✅   | ✅    | ✅        | Sprint 1 flow `48:1089`                                                          |
| 2     | Mobile Trends         | ✅   | ✅    | ✅        | Sprint 2 flow `59:1285`                                                          |
| 3     | Mobile Insights       | ✅   | ✅    | ✅        | [`MOBILE_INSIGHTS_PHASE3_SPRINT_PLAN.md`](MOBILE_INSIGHTS_PHASE3_SPRINT_PLAN.md) |
| 4     | Supporting flows      | ✅   | ✅    | ✅        | This document, Sprint 4 below                                                    |
| 5     | Desktop consolidation | —    | —     | —         | **Out of scope**                                                                 |

---

## Sprint A — Phase 3 QA & closeout ✅

**Completed 2026-06-26.** QA doc: [`docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`](quality/MOBILE_INSIGHTS_PHASE3_QA.md).

**Depends on:** Sprint 1 Figma parity ✅

**Goal:** Sign off rendered mobile Insights against Figma Sprint 3 reference and
close Phase 3 documentation.

| #   | Task                                                          | Owner    | Exit                                                                                         |
| --- | ------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| A1  | Rendered QA matrix 390/430/1280, light+dark                   | Frontend | ✅ `docs/quality/MOBILE_INSIGHTS_PHASE3_QA.md`                                               |
| A2  | Dev Mode maturity phase walkthrough                           | Frontend | ✅ Four phases (component + route contract)                                                  |
| A3  | E2E: `mobile-insights-foundation`, `m7-insights-mobile` green | CI       | ✅ Pass on #234 merge; CI Web green @ `7b7ca8a`                                              |
| A4  | Update `MOBILE_WEB_IMPLEMENTATION_PLAN.md` Phase 3 → complete | Docs     | ✅                                                                                           |
| A5  | `CHANGELOG.md` Mobile Insights Phase 3 entry                  | Docs     | ✅                                                                                           |
| A6  | Rescope GitHub #200 (note composer → M8)                      | Product  | ✅ [#200 comment](https://github.com/Sturmi77/correlcore/issues/200#issuecomment-4811455402) |

**Definition of done:** Phase 3 row in phase ledger shows ✅ for QA/Docs.

---

## Sprint B — Phase 4 Figma parity ✅

**Completed 2026-06-26** in Figma file
[CorrelCore Design System](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS).

Flow board: [`Mobile Supporting Flows / Sprint 4 Flow`](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=105-1626) (`105:1626`, **1680 px** wide, 22 screens at **390×844**)

| Group               | Screens                                    | Node IDs                                |
| ------------------- | ------------------------------------------ | --------------------------------------- |
| B1 Settings         | Default                                    | `105:1634`                              |
| B2 Symptoms         | Default, Delete, Empty                     | `105:1679`–`105:1755`                   |
| B2 Symptoms (cont.) | Loading, Error                             | `105:1787`, `105:1819` (row `111:2120`) |
| B3 App & Offline    | Online, Offline, Install unavailable       | `105:1855`–`105:1939`                   |
| B4 Auth             | Verify idle/busy/success                   | `105:1978`–`105:2032`                   |
| B4 Auth (cont.)     | Verify error, Missing token                | `105:2060`, `105:2088` (row `111:2123`) |
| B4 Resend           | Success, Error                             | `105:2119`, `105:2127`                  |
| B5 Onboarding       | Guided tags, Retrospective, Profile, Error | `105:2176`–`105:2164`                   |
| B6 Overlays         | Offline banner, Update banner              | `105:2190`, `105:2228`                  |

Layout cleanup (2026-06-26): auto-layout sizing fixed (no clipped 100 px rows);
wide B2/B4 groups split into continuation rows to match Sprint 3 board width.

Components used: `ScreenHeader`, `Panel`, `Button`, `InlineAlert`, `FormField`,
`AppNav`. No background sync queue depicted (ADR-0009).

Node index: [`apps/web/figma/README.md`](../apps/web/figma/README.md)

---

## Sprint C — Cross-phase mobile QA sign-off ✅

**Completed 2026-06-27.** QA doc: [`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md`](quality/MOBILE_WEB_CLOSEOUT_QA.md).

**Depends on:** Sprint A + Sprint B

**Goal:** One signed mobile QA pass across all primary flows at baseline
viewports (ADR-0017 / Sprint 0 contract).

### Viewports

390 × 844, 430 × 932 (mandatory mobile); 768 × 1024 optional sanity check.
**1280 px:** confirm mobile-specific surfaces hidden (e.g. `MobileInsightLead`),
not full desktop consolidation.

### Screens

| Screen            | Code route                 | Figma reference     | E2E spec                     |
| ----------------- | -------------------------- | ------------------- | ---------------------------- |
| Entry             | `/entries/*`               | Sprint 1 `48:1089`  | `mobile-entry-foundation`    |
| Trends            | `/trends`                  | Sprint 2 `59:1285`  | `mobile-trends-foundation`   |
| Insights          | `/insights`                | Sprint 3 `98:1573`  | `mobile-insights-foundation` |
| Settings / PWA    | `/settings`, `/offline`    | Sprint 4 `105:1626` | `mobile-supporting-flows`    |
| Onboarding / Auth | `/onboarding/*`, `/auth/*` | Sprint 4 (after B)  | partial in supporting flows  |

### Deliverable

`docs/quality/MOBILE_WEB_CLOSEOUT_QA.md` — matrix with light/dark, h-scroll
check, touch target spot-check (44 px nav), and known deferrals.

**Definition of done:** All primary mobile flows signed; open defects tracked as
GitHub issues with `mobile` label. ✅

---

## Sprint D — Documentation & GitHub closure ✅

**Completed 2026-06-27.**

**Depends on:** Sprint C

| #   | Task                                                                                                          | Exit                               |
| --- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| D1  | Set `MOBILE_WEB_IMPLEMENTATION_PLAN.md` header status to **mobile closeout complete** (Phases 0–4)            | ✅ Doc on `main`                   |
| D2  | Refresh `MOBILE_WEB_AUDIT.md` status matrix (Insights yellow→green, Settings/Auth/Offline where Figma exists) | ✅ Audit + `mobile-web-audit.json` |
| D3  | Close or rescope open mobile GitHub issues (#200, partial #214 mobile items)                                  | ✅ #200 closed; #214 closed        |
| D4  | `MobileInsightLead.figma.ts` Code Connect template                                                            | ✅ `apps/web/figma/components/`    |

---

## Explicitly out of scope

- **Phase 5 desktop consolidation** (wide-screen density, split views)
- Capacitor / Health Connect (M11 / M8) — tracked separately (#27, #31)
- Dexie full offline sync queue (M4 follow-up, ADR-0009)
- Password recovery, reminders, account deletion (backend contracts pending)
- Published-library Code Connect activation (Figma seat/plan gate)

---

## Recommended execution order

```text
Sprint A (Phase 3 QA) → Sprint B (Phase 4 Figma) → Sprint C (cross-phase QA) → Sprint D (docs/GitHub)
```

Parallel work allowed:

- M5.1 UX follow-ups (#214) that touch mobile Trends/Insights — must not break
  Sprint A E2E assertions
- Backend-only M8/M7 items — no mobile plan dependency

---

## Risk register

| Risk                                      | Mitigation                                               |
| ----------------------------------------- | -------------------------------------------------------- |
| Figma `28:615` used as Insights reference | README + plan mark outdated; Sprint 3 nodes canonical    |
| Rendered QA blocked locally               | Use CI Playwright + manual device pass for PWA install   |
| Phase 4 Figma scope creep                 | Stick to states already implemented in code (#234)       |
| Desktop changes regress mobile            | Keep 768 px breakpoint contract; no Phase 5 in this plan |
