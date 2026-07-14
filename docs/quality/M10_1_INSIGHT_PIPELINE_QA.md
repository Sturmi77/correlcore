# M10.1 Insight Pipeline — Visual & Integration QA

Last updated: 2026-07-13

Manual QA checklist for [M10.1 Insight Pipeline](../M10_1_INSIGHT_PIPELINE_SPRINT_PLAN.md).
Run after Pakete A–E are merged.

## Prerequisites

- Worker running **or** `POST /insights/regenerate` / Settings → **Refresh insights**
- Test user with ≥ 45 tracking days and diverse tags (M7 QA seed or import)
- `analytics_enabled = true`

## Trigger & Insights

| #   | Step                                                        | Expected                                                  |
| --- | ----------------------------------------------------------- | --------------------------------------------------------- |
| T1  | Fresh user, 67 days imported via batch, no prior worker run | After import (or regenerate): `/insights` shows ≥ 1 card  |
| T2  | `POST /insights/regenerate` twice within 60 min             | Second call rate-limited (429)                            |
| T3  | Disable analytics in Settings, call regenerate              | No new insights / 403                                     |
| T4  | Home Daily Brief after regenerate                           | Lead statement from top insight (not only maturity phase) |

## Tag-Gruppen

| #   | Days          | Expected                                            |
| --- | ------------- | --------------------------------------------------- |
| G1  | 25            | Insufficient copy mentions 30-day threshold         |
| G2  | 35            | `pair` mode groups (2–3 tags), early maturity badge |
| G3  | 67            | `provisional` badge, ≥ 1 cluster, strength % shown  |
| G4  | 90+ (M7 seed) | `robust`, full k-means, no provisional badge        |

## Wochentags-Übersicht (Home)

| #   | Step                                      | Expected                          |
| --- | ----------------------------------------- | --------------------------------- |
| W1  | 67 days, flat mood (no `weekday_pattern`) | Seven weekday bars with averages  |
| W2  | User with strong weekday pattern          | Bars + optional pattern statement |
| W3  | &lt; 7 days                               | Empty state with hint             |

## Insights feed empty states

| #   | Step | Expected |
| --- | ---- | -------- |
| F1  | 67 days, flat metrics, regenerate → `insight_count: 0`, phase `robust` | Feed shows robust empty copy (maturity ≠ cards) + **Refresh insights** CTA; subtitle may still show ~67 entries |
| F2  | Insights exist but filter tab Mood/Symptoms/Context matches none | Generic filter-empty copy — **not** `empty_phase.robust` |
| F3  | Distinguish `GET /insights/latest` vs `GET /insights` | Both empty ⇒ no persisted rows; latest empty but list non-empty ⇒ investigate subject dedupe |

**Note:** Entry count / ADR-0021 maturity advances independently of whether statistical gates (`MIN_WEEKDAY_DELTA`, tag usages, FDR, etc.) produced cards. A populated analysis window does not guarantee insight cards.

## Regression

| #   | Check                                              |
| --- | -------------------------------------------------- |
| R1  | Lasso/lag insights still only at 90+ days          |
| R2  | Point-biserial still requires 10+ tag usages       |
| R3  | Nightly worker still runs without error in compose |

## Sign-off

| Role    | Name | Date | Pass |
| ------- | ---- | ---- | ---- |
| Dev     |      |      |      |
| Product |      |      |      |
