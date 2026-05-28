# M3.6 Visual QA Closeout

Date: 2026-05-27

Scope: Insight maturity phases (ADR-0021) — Journey Banner, Maturity Badge, phase-aware empty states, and phase milestone cards.

## Result

**M3.6 release closeout: passed.**

Rendered browser QA was executed from the local clone `C:\Users\micha\correlcore-ci` against `main` at `70bb5ed` via `pnpm.cmd dev` on `http://localhost:5173/`. All four maturity phases and core M3.6 UI surfaces completed without blocking defects.

## Phase Matrix

| Phase            | Entry range | Surfaces verified                                      | Status |
| ---------------- | ----------- | ------------------------------------------------------ | ------ |
| `collecting`     | 1–6         | Journey Banner, empty/locked copy, no premature badges | Pass   |
| `early_patterns` | 7–13        | Badge, uncertainty hints, Journey progress             | Pass   |
| `provisional`    | 14–29       | Badge, locked sections, phase-aware messaging          | Pass   |
| `robust`         | 30+         | Confirmed badge, populated insight feed                | Pass   |

## Viewport & Theme

| Check              | Status |
| ------------------ | ------ |
| 375 x 812 mobile   | Pass   |
| 1280 x 800 desktop | Pass   |
| Light mode         | Pass   |
| Dark mode          | Pass   |

## Core Interactions

| Interaction                             | Rendered QA |
| --------------------------------------- | ----------- |
| InsightJourneyBanner on `/insights`     | Pass        |
| Collapsible Journey Banner on Home      | Pass        |
| InsightJourneyExplainer (`[?]` button)  | Pass        |
| InsightMaturityBadge on insight cards   | Pass        |
| Phase milestone card + explicit dismiss | Pass        |
| DE/EN `maturity.*` copy                 | Pass        |

## Evidence

- Phase coverage via Dev Mode → Force Visualizations and authenticated flows.
- GitHub issues #188–#192 closed as implemented on 2026-05-26.
- Automated regression: GitHub `CI — Web` on `70bb5ed`.
