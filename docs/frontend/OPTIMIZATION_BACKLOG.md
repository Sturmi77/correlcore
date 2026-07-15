# CorrelCore — GUI Optimization Backlog

**Date:** 2026-06-30 (updated 2026-07-10 — M5.1 UX polish closeout)  
**Epic PR:** [#255](https://github.com/Sturmi77/correlcore/pull/255)  
**Implementation plan:** [`GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md`](GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md)  
**Source audit:** [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md) · [`USER_WORKFLOWS.md`](USER_WORKFLOWS.md)  
**Milestone closeout:** [`../M5_1_UX_POLISH_PLAN.md`](../M5_1_UX_POLISH_PLAN.md) · [`../M5_1_SPRINT_STATUS.md`](../M5_1_SPRINT_STATUS.md)

> **O-01–O-20:** Implementation complete (PRs #281, #284). Formal M5.1 milestone
> closeout 2026-07-10. #272 (O-20 password reset) shipped in PR #284; tracker
> hygiene closed 2026-07-15.

---

## Issue index (O-01 – O-20)

| ID   | GitHub                                                    | Sprint | Status | Title                                                                         |
| ---- | --------------------------------------------------------- | ------ | ------ | ----------------------------------------------------------------------------- |
| O-01 | [#250](https://github.com/Sturmi77/correlcore/issues/250) | A      | Done   | Consolidate Insights maturity UI on mobile                                    |
| O-02 | [#251](https://github.com/Sturmi77/correlcore/issues/251) | A      | Done   | Open EntrySheet after onboarding complete                                     |
| O-03 | [#252](https://github.com/Sturmi77/correlcore/issues/252) | A      | Done   | Insights empty-state CTA opens entry directly                                 |
| O-04 | [#253](https://github.com/Sturmi77/correlcore/issues/253) | B      | Done   | Redirect legacy onboarding routes                                             |
| O-05 | [#254](https://github.com/Sturmi77/correlcore/issues/254) | A      | Done†  | Hide Home sparkline until ≥3 entries                                          |
| O-06 | [#260](https://github.com/Sturmi77/correlcore/issues/260) | C      | Done   | Integrate tag selection into first entry                                      |
| O-07 | [#261](https://github.com/Sturmi77/correlcore/issues/261) | C      | Done   | Auto-login after email verification                                           |
| O-08 | [#262](https://github.com/Sturmi77/correlcore/issues/262) | E      | Done   | Unify desktop entry surface                                                   |
| O-09 | [#263](https://github.com/Sturmi77/correlcore/issues/263) | B      | Done   | Habit hint in onboarding tag step                                             |
| O-11 | [#273](https://github.com/Sturmi77/correlcore/issues/273) | B      | Done   | Check-email mobile mail-app deep link                                         |
| O-12 | [#264](https://github.com/Sturmi77/correlcore/issues/264) | D      | Done   | Home Daily Brief brief-first layout                                           |
| O-13 | [#266](https://github.com/Sturmi77/correlcore/issues/266) | D      | Done   | Home bridge for weekly analysis review                                        |
| O-14 | [#268](https://github.com/Sturmi77/correlcore/issues/268) | B      | Done   | Gate Insights matrix/co-occurrence by maturity                                |
| O-15 | [#271](https://github.com/Sturmi77/correlcore/issues/271) | D      | Done   | Trends global sticky range control (desktop)                                  |
| O-16 | [#265](https://github.com/Sturmi77/correlcore/issues/265) | B      | Done   | Inline habit setup on empty Habits panel                                      |
| O-17 | [#267](https://github.com/Sturmi77/correlcore/issues/267) | E      | Done   | Heatmap drill-down via EntryHistorySheet                                      |
| O-18 | [#269](https://github.com/Sturmi77/correlcore/issues/269) | F      | Done   | Defer PWA install banner until after first entry                              |
| O-19 | [#270](https://github.com/Sturmi77/correlcore/issues/270) | F      | Done   | Improve export discoverability in Settings                                    |
| O-20 | [#272](https://github.com/Sturmi77/correlcore/issues/272) | G      | Done   | Password reset — [`O-20_PASSWORD_RESET_PLAN.md`](O-20_PASSWORD_RESET_PLAN.md) |

† O-05 satisfied via Phase-3 O-55 (sparkline removed from Home).

> **Note:** O-10 is intentionally unused (reserved). Former “O-10 password / O-11 Phase 5 / O-12 Figma” map to **O-20**, **O-08**, and out-of-scope Figma Sprint H respectively.

**Phase 2 (O-21–O-42):** **Complete** (July 2026) — see [`GUI_OPTIMIZATION_PHASE2.md`](GUI_OPTIMIZATION_PHASE2.md). Residual polish **O-01 / O-14** closed in Phase-2 closure PR.

**Phase 3 (O-43–O-56):** **Open** — see [`GUI_OPTIMIZATION_PHASE3.md`](GUI_OPTIMIZATION_PHASE3.md). User findings: Heute brief + Erkenntnisse mobile/interpretability.

**Phase 4 (O-57–O-62):** **Open** — see [`GUI_OPTIMIZATION_PHASE4.md`](GUI_OPTIMIZATION_PHASE4.md). Mobile UX findings: Home CTA, weekday overview, heatmap density, Trends sticky chrome, Insights overflow.

**Phase 4 follow-up (O-63–O-64):** **Open** — see [`GUI_OPTIMIZATION_PHASE4.md`](GUI_OPTIMIZATION_PHASE4.md#phase-4-follow-up-o-63o-64). Home work-context encoding + Trends mobile control density.

---

## Issue index (O-63 – O-64) — Phase 4 follow-up

| ID   | Sprint | Impact | Effort | Status | Title                                                         |
| ---- | ------ | ------ | ------ | ------ | ------------------------------------------------------------- |
| O-63 | P4-D   | High   | Low    | Open   | Home: encode work-context bars by mood, not entry frequency   |
| O-64 | P4-C   | High   | Medium | Open   | Trends mobile: compact quick filters + compare settings sheet |

GitHub follow-up PR: branch `cursor/home-trends-followup-e965`

---

## Issue index (O-57 – O-62) — Phase 4

| ID   | Sprint | Impact   | Effort | Status | Title                                                        |
| ---- | ------ | -------- | ------ | ------ | ------------------------------------------------------------ |
| O-57 | P4-D   | High     | Low    | Open   | Home: single primary CTA when today has no entry             |
| O-58 | P4-D   | High     | Medium | Open   | Home: weekday overview with per-day findings                 |
| O-59 | P4-B   | Medium   | Medium | Open   | Heatmaps: hide empty rows/columns in selected range (mobile) |
| O-60 | P4-C   | High     | Medium | Open   | Trends: fixed Y-axis / legend on horizontal scroll           |
| O-61 | P4-C   | Medium   | Medium | Open   | Trends: floating toolbar like Insights (incl. mobile)        |
| O-62 | P4-A   | Critical | Medium | Open   | Insights: Symptom calendar/progression viewport overflow fix |

GitHub: [#338](https://github.com/Sturmi77/correlcore/issues/338) — `[UX] Mobile: Home-CTA, Wochentags-Übersicht, Heatmap-Dichte, Trends-Sticky, Insights-Overflow`

---

## Issue index (O-43 – O-56) — Phase 3

| ID   | Sprint | Impact   | Effort | Status | Title                                                              |
| ---- | ------ | -------- | ------ | ------ | ------------------------------------------------------------------ |
| O-43 | P3-A   | Critical | Medium | Open   | Fix mobile Insights empty state when insights exist (robust phase) |
| O-44 | P3-A   | High     | Low    | Open   | Stale-while-revalidate for Insights feed during reload             |
| O-45 | P3-A   | High     | Low    | Open   | SSR-safe `compactInsights` (no mobile layout flash)                |
| O-46 | P3-A   | Medium   | Low    | Open   | InsightFeed subtitle follows `analysisRange`, not fixed 90d        |
| O-47 | P3-B   | High     | Medium | Open   | Insights zweizeilige sticky toolbar (range + filter)               |
| O-48 | P3-B   | High     | Medium | Open   | Permanent analytics section (remove accordion)                     |
| O-49 | P3-B   | High     | Low    | Open   | Symptom analytics decoupled from filter tab (revise O-24)          |
| O-50 | P3-C   | High     | Medium | Open   | Insights heatmaps: responsive axis layout (Trends parity)          |
| O-51 | P3-C   | High     | Medium | Open   | SymptomTrendOverlay responsive + readable axes                     |
| O-52 | P3-C   | High     | Low    | Open   | Mobile Insights: cap analysis range at 90d (quarter)               |
| O-53 | P3-C   | Medium   | Medium | Open   | Symptom calendar legend + interpretation copy                      |
| O-54 | P3-D   | High     | Low    | Open   | Remove Home Zone-3 CTA when today's entry exists                   |
| O-55 | P3-D   | Medium   | Low    | Open   | Remove Home sparkline (O-05 reversed)                              |
| O-56 | P3-D   | High     | Medium | Open   | Home Daily Brief: facts row → Top Insight snippet                  |

---

## Sprint execution order (Phase 3)

| Sprint                 | Issues    | Goal                                  |
| ---------------------- | --------- | ------------------------------------- |
| **P3-A — Mobile fix**  | O-43–O-46 | Insights render correctly on phone    |
| **P3-B — Insights IA** | O-47–O-49 | Toolbar + permanent analytics         |
| **P3-C — Charts**      | O-50–O-53 | Interpretable charts, mobile 90d cap  |
| **P3-D — Home brief**  | O-54–O-56 | Single CTA, no sparkline, top insight |

See [`GUI_OPTIMIZATION_PHASE3.md`](GUI_OPTIMIZATION_PHASE3.md) for root causes, acceptance criteria, and PR branch names.

---

## Issue index (O-21 – O-42) — Phase 2

| ID   | Sprint | Impact | Effort | Status            | Title                                             |
| ---- | ------ | ------ | ------ | ----------------- | ------------------------------------------------- |
| O-21 | H      | High   | Medium | **Done** #289     | Entry: tags/symptoms/time slots always visible    |
| O-30 | H      | Medium | Low    | **Done** #288     | Spacing foundation (`screen-stack`, tokens)       |
| O-23 | H      | High   | Medium | **Done** Sprint H | Global `analysisRange` (Trends + Insights)        |
| O-22 | H      | High   | Medium | **Done** Sprint H | Insights single control row (chips + matrix link) |
| O-24 | H      | Medium | Low    | **Done** Sprint H | Symptom analytics via category filter             |
| O-40 | I      | Medium | Medium | **Done** Sprint I | Cross-link Trends ↔ Insights top finding          |
| O-41 | M      | Medium | High   | **Done** Sprint M | Trends Compare + Health tab consolidation         |
| O-39 | I      | Medium | Low    | **Done** Sprint I | Home brief: entries-until-milestone inline        |
| O-36 | J      | Medium | Medium | **Done** Sprint J | Smart entry defaults from yesterday               |
| O-08 | J      | Medium | High   | **Done** Sprint J | Unify desktop entry surface                       |
| O-38 | J      | Medium | Low    | **Done** Sprint J | Empty CTAs open EntrySheet inline                 |
| O-37 | K      | Medium | Medium | **Done** Sprint K | Onboarding: skip summary ≤3 tags, merge intro     |
| O-09 | K      | Medium | Medium | **Done** Sprint K | Habit hint in onboarding tag step                 |
| O-26 | L      | Medium | Low    | **Done** Sprint L | Trends mobile detail toggle vs scroll             |
| O-29 | L      | Low    | Low    | **Done** Sprint L | Compare filters only when mobile detail open      |
| O-31 | L      | Low    | Low    | **Done** Sprint L | Settings sub-routes → `screen-stack`              |
| O-32 | L      | Low    | Low    | **Done** Sprint L | Heatmap micro-gaps → tokens                       |
| O-33 | L      | Low    | Low    | **Done** Sprint L | `ScreenHeader` gap token                          |
| O-34 | L      | Medium | Low    | **Done** Sprint L | Compact InsightStageHeader on mobile              |
| O-35 | L      | Low    | Low    | **Done** Sprint L | Contract test: no double route padding            |
| O-25 | M      | Medium | High   | **Done** Sprint M | Entry quick vs full at open                       |
| O-27 | M      | Low    | Medium | **Done** Sprint M | Settings vocabulary hub (W8)                      |
| O-28 | M      | Medium | High   | **Done** Sprint M | Account deletion (M9)                             |
| O-42 | M      | Low    | Low    | **Done** Sprint M | Time slots in date row                            |
| —    | Polish | Medium | Low    | **Done** Closure  | O-01 maturity badge dedup; O-14 analytics gates   |

**Phase 2 status:** all O-21–O-42 items **Done** (Sprints H–M + polish closure). [`GUI_OPTIMIZATION_PHASE2.md` §3](GUI_OPTIMIZATION_PHASE2.md#3-friction-audit--abdeckungsmatrix)

---

## Issue index (O-43 – O-56) — Phase 3

| ID   | Sprint | Impact   | Effort | Status   | Title                                             |
| ---- | ------ | -------- | ------ | -------- | ------------------------------------------------- |
| O-43 | P3-A   | Critical | Medium | **Done** | Fix mobile Insights feed empty-state gap          |
| O-44 | P3-A   | High     | Low    | **Done** | Stale-while-revalidate insight loading            |
| O-45 | P3-A   | High     | Low    | **Done** | SSR-safe `compactInsights` hydration              |
| O-46 | P3-A   | Medium   | Low    | **Done** | Dynamic InsightFeed subtitle from `analysisRange` |
| O-47 | P3-B   | High     | Medium | **Done** | Two-row Insights analysis toolbar                 |
| O-48 | P3-B   | High     | Medium | **Done** | Permanent analytics (no accordion)                |
| O-49 | P3-B   | High     | Low    | **Done** | Decouple symptom analytics from filter tab        |
| O-50 | P3-C   | High     | Medium | **Done** | Responsive heatmap axis on Insights               |
| O-51 | P3-C   | High     | Medium | **Done** | Responsive `SymptomTrendOverlay`                  |
| O-52 | P3-C   | High     | Low    | **Done** | Mobile Insights 90d range cap                     |
| O-53 | P3-C   | Medium   | Medium | **Done** | Symptom calendar legend + interpretation          |
| O-54 | P3-D   | High     | Low    | **Done** | Conditional Home Zone-3 CTA                       |
| O-55 | P3-D   | Medium   | Low    | **Done** | Remove Home sparkline                             |
| O-56 | P3-D   | High     | Medium | **Done** | Home facts row → Top Insight snippet              |

**Phase 3 status:** all O-43–O-56 items **Done** — see [`GUI_OPTIMIZATION_PHASE3.md`](GUI_OPTIMIZATION_PHASE3.md).

---

## Sprint execution order (Phase 2)

| Sprint                  | Issues              | Goal                          |
| ----------------------- | ------------------- | ----------------------------- |
| **H — Analyse-Kern**    | O-23, O-22, O-24 ✅ | Insights IA complete          |
| **I — Home & Links**    | O-39, O-40, O-13 ✅ | Weekly review bridge complete |
| **J — Entry & Desktop** | O-36, O-08, O-38 ✅ | W3/W4 audit rest              |

| **K — Onboarding & Habits** | O-37, O-09 ✅ | W2/W7 audit rest |
| **L — Spacing & Polish** | O-31–O-35, O-26, O-29, O-34 ✅ | Mobile density |
| **M — Strategic** | O-41, O-25, O-27, O-28, O-42 ✅ | Larger IA / backend |
| **Polish — Closure** | O-01, O-14 ✅ | Maturity dedup + analytics gates |

---

## Workflow coverage matrix (Phase 2 additions)

| Workflow           | Open Phase-2 issues                                        |
| ------------------ | ---------------------------------------------------------- |
| W1 Account         | — (complete)                                               |
| W2 Onboarding      | ~~O-37~~, ~~O-09~~                                         |
| W3 Daily entry     | ~~O-36~~, ~~O-08~~, ~~O-38~~, ~~O-21~~, ~~O-25~~, ~~O-42~~ |
| W4 Backdate        | ~~O-08~~                                                   |
| W5 First insight   | ~~O-34~~, ~~O-01~~                                         |
| W6 Weekly analysis | ~~O-41~~, ~~O-26~~, ~~O-29~~, ~~O-14~~                     |
| W7 Habits          | ~~O-09~~                                                   |
| W8 Vocabulary      | ~~O-27~~, ~~O-28~~                                         |
| W9 Export          | — (complete)                                               |
| W10 PWA            | — (complete)                                               |

---

## Sprint execution order

See [`GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md`](GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md) for dependencies, technical patterns, and exit criteria.

| Sprint                    | Issues                        | Goal                               |
| ------------------------- | ----------------------------- | ---------------------------------- |
| **A — Quick wins**        | #250, #251, #252, #254        | First-week friction removal        |
| **B — Cleanup**           | #253, #263, #268, #265, #273  | Legacy paths, habits, matrix gates |
| **C — Auth & onboarding** | #261, #260 (after #251)       | Shorter new-user funnel            |
| **D — Analysis IA**       | #264, #266, #271 (after #250) | Brief-first Home, weekly review    |
| **E — Desktop polish**    | #262, #267                    | Entry surface + drill-down         |
| **F — Deferred backlog**  | #269, #270                    | PWA timing, export UX              |
| **G — Password reset**    | #272                          | Forgot/reset flow (O-20)           |
| **Blocked**               | —                             | —                                  |

---

## Workflow coverage matrix

| Workflow           | Issues                             |
| ------------------ | ---------------------------------- |
| W1 Account         | #261, #273, #272                   |
| W2 Onboarding      | #251, #253, #260, #263             |
| W3 Daily entry     | #251, #260, #262                   |
| W4 Backdate        | #262, #267                         |
| W5 First insight   | #250, #252, #254, #264, #268       |
| W6 Weekly analysis | #250, #264, #266, #268, #271, #267 |
| W7 Habits          | #263, #265                         |
| W8 Vocabulary      | — (low friction, no ticket)        |
| W9 Export          | #270                               |
| W10 PWA            | #269                               |

---

## Optimization classes legend

`Eliminieren` · `Vorverlagern` · `Zusammenführen` · `Vereinfachen` · `Umleiten` · `Nicht ändern`

---

## Governance

- No 6th nav tab (ADR-0017)
- No gamification (DESIGN_DOCUMENT §1.4)
- Insight maturity model unchanged in meaning (ADR-0021); display may consolidate
- ADR required before: #260 (ADR-0030), #261 (ADR-0004)

---

## Regression commands

```bash
pnpm lint && pnpm typecheck && pnpm test
pnpm --filter @correlcore/web test:e2e:journeys --workers=1
pnpm --filter @correlcore/web test:e2e:mobile --workers=1
pnpm --filter @correlcore/web test:e2e:smoke
```
