# CorrelCore — GUI Optimization Backlog

**Date:** 2026-06-30  
**Epic PR:** [#255](https://github.com/Sturmi77/correlcore/pull/255)  
**Implementation plan:** [`GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md`](GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md)  
**Source audit:** [`FRICTION_AUDIT.md`](FRICTION_AUDIT.md) · [`USER_WORKFLOWS.md`](USER_WORKFLOWS.md)

---

## Issue index (O-01 – O-20)

| ID   | GitHub                                                    | Sprint | Impact | Effort | Title                                                                         |
| ---- | --------------------------------------------------------- | ------ | ------ | ------ | ----------------------------------------------------------------------------- |
| O-01 | [#250](https://github.com/Sturmi77/correlcore/issues/250) | A      | High   | Low    | Consolidate Insights maturity UI on mobile                                    |
| O-02 | [#251](https://github.com/Sturmi77/correlcore/issues/251) | A      | High   | Low    | Open EntrySheet after onboarding complete                                     |
| O-03 | [#252](https://github.com/Sturmi77/correlcore/issues/252) | A      | Medium | Low    | Insights empty-state CTA opens entry directly                                 |
| O-04 | [#253](https://github.com/Sturmi77/correlcore/issues/253) | B      | Medium | Low    | Redirect legacy onboarding routes                                             |
| O-05 | [#254](https://github.com/Sturmi77/correlcore/issues/254) | A      | Low    | Low    | Hide Home sparkline until ≥3 entries                                          |
| O-06 | [#260](https://github.com/Sturmi77/correlcore/issues/260) | C      | High   | High   | Integrate tag selection into first entry                                      |
| O-07 | [#261](https://github.com/Sturmi77/correlcore/issues/261) | C      | High   | Medium | Auto-login after email verification                                           |
| O-08 | [#262](https://github.com/Sturmi77/correlcore/issues/262) | E      | Medium | High   | Unify desktop entry surface                                                   |
| O-09 | [#263](https://github.com/Sturmi77/correlcore/issues/263) | B      | Medium | Medium | Habit hint in onboarding tag step                                             |
| O-11 | [#273](https://github.com/Sturmi77/correlcore/issues/273) | B      | Low    | Low    | Check-email mobile mail-app deep link                                         |
| O-12 | [#264](https://github.com/Sturmi77/correlcore/issues/264) | D      | High   | Medium | Home Daily Brief brief-first layout                                           |
| O-13 | [#266](https://github.com/Sturmi77/correlcore/issues/266) | D      | Medium | Medium | Home bridge for weekly analysis review                                        |
| O-14 | [#268](https://github.com/Sturmi77/correlcore/issues/268) | B      | Medium | Low    | Gate Insights matrix/co-occurrence by maturity                                |
| O-15 | [#271](https://github.com/Sturmi77/correlcore/issues/271) | D      | Medium | Medium | Trends global sticky range control (desktop)                                  |
| O-16 | [#265](https://github.com/Sturmi77/correlcore/issues/265) | B      | Medium | Medium | Inline habit setup on empty Habits panel                                      |
| O-17 | [#267](https://github.com/Sturmi77/correlcore/issues/267) | E      | Medium | Medium | Heatmap drill-down via EntryHistorySheet                                      |
| O-18 | [#269](https://github.com/Sturmi77/correlcore/issues/269) | F      | Medium | Low    | Defer PWA install banner until after first entry                              |
| O-19 | [#270](https://github.com/Sturmi77/correlcore/issues/270) | F      | Low    | Low    | Improve export discoverability in Settings                                    |
| O-20 | [#272](https://github.com/Sturmi77/correlcore/issues/272) | G      | Medium | High   | Password reset — [`O-20_PASSWORD_RESET_PLAN.md`](O-20_PASSWORD_RESET_PLAN.md) |

> **Note:** O-10 is intentionally unused (reserved). Former “O-10 password / O-11 Phase 5 / O-12 Figma” map to **O-20**, **O-08**, and out-of-scope Figma Sprint H respectively.

**Phase 2 (O-21+):** see [`GUI_OPTIMIZATION_PHASE2.md`](GUI_OPTIMIZATION_PHASE2.md) — vollständiger Plan inkl. offener Friction-Audit-Punkte.

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
| O-41 | M      | Medium | High   | Open              | Trends Compare + Health tab consolidation         |
| O-39 | I      | Medium | Low    | **Done** Sprint I | Home brief: entries-until-milestone inline        |
| O-36 | J      | Medium | Medium | **Done** Sprint J | Smart entry defaults from yesterday               |
| O-08 | J      | Medium | High   | **Done** Sprint J | Unify desktop entry surface                       |
| O-38 | J      | Medium | Low    | **Done** Sprint J | Empty CTAs open EntrySheet inline                 |
| O-37 | K      | Medium | Medium | Partial           | Onboarding: skip summary ≤3 tags, merge intro     |
| O-09 | K      | Medium | Medium | Partial           | Habit hint in onboarding tag step                 |
| O-26 | L      | Medium | Low    | Open              | Trends mobile detail toggle vs scroll             |
| O-29 | L      | Low    | Low    | Open              | Compare filters only when mobile detail open      |
| O-31 | L      | Low    | Low    | Open              | Settings sub-routes → `screen-stack`              |
| O-32 | L      | Low    | Low    | Open              | Heatmap micro-gaps → tokens                       |
| O-33 | L      | Low    | Low    | Open              | `ScreenHeader` gap token                          |
| O-34 | L      | Medium | Low    | Open              | Compact InsightStageHeader on mobile              |
| O-35 | L      | Low    | Low    | Open              | Contract test: no double route padding            |
| O-25 | M      | Medium | High   | Open              | Entry quick vs full at open                       |
| O-27 | M      | Low    | Medium | Open              | Settings vocabulary hub (W8)                      |
| O-28 | M      | Medium | High   | Open              | Account deletion (M9)                             |
| O-42 | M      | Low    | Low    | Open              | Time slots in date row                            |

**Audit mapping:** [`GUI_OPTIMIZATION_PHASE2.md` §3](GUI_OPTIMIZATION_PHASE2.md#3-friction-audit--abdeckungsmatrix)

---

## Sprint execution order (Phase 2)

| Sprint                      | Issues                       | Goal                          |
| --------------------------- | ---------------------------- | ----------------------------- |
| **H — Analyse-Kern**        | O-23, O-22, O-24 ✅          | Insights IA complete          |
| **I — Home & Links**        | O-39, O-40, O-13 ✅          | Weekly review bridge complete |
| **J — Entry & Desktop**     | O-36, O-08, O-38 ✅          | W3/W4 audit rest              |
| **K — Onboarding & Habits** | O-37, O-09                   | W2/W7 audit rest              |
| **L — Spacing & Polish**    | O-31–O-35, O-26, O-29, O-34  | Mobile density                |
| **M — Strategic**           | O-41, O-25, O-27, O-28, O-42 | Larger IA / backend           |

---

## Workflow coverage matrix (Phase 2 additions)

| Workflow           | Open Phase-2 issues                    |
| ------------------ | -------------------------------------- |
| W1 Account         | — (complete)                           |
| W2 Onboarding      | O-37                                   |
| W3 Daily entry     | ~~O-36~~, ~~O-08~~, ~~O-38~~, ~~O-21~~ |
| W4 Backdate        | ~~O-08~~                               |
| W5 First insight   | O-34                                   |
| W6 Weekly analysis | O-41, O-26, O-29                       |
| W7 Habits          | O-09                                   |
| W8 Vocabulary      | O-27                                   |
| W9 Export          | — (complete)                           |
| W10 PWA            | — (complete)                           |

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
