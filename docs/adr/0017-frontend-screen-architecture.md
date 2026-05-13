# ADR-0017 — Frontend Screen Architecture (M3.1)

## Status

Accepted (2026-05-13)

## Context

With M3 delivering the first real statistical insights (Spearman, point-biserial, weekday patterns via the nightly analytics worker), the existing frontend structure is insufficient. The home screen sketch in the previous `FRONTEND.md` still showed `[Streak: 🔥 7]`, directly contradicting the No-Gamification Promise (§1.4 DESIGN_DOCUMENT). No formal screen inventory or navigation contract existed. M3.1 defines the canonical screen architecture that all subsequent milestones build on.

Market analysis of competitors (Daylio, Bearable, Exist.io, Correlate iOS) identified:

- Daylio: entry speed is best-in-class; insight presentation is an anti-pattern (frequency counts, no statistical validity signal)
- Bearable: correlation as USP works; configuration overhead and cloud-only are differentiators CorrelCore can exploit
- Exist.io: dual strength+confidence metric is state-of-the-art; formulations are too abstract for lifestyle users
- Correlate (iOS): dual-axis charts + auto-discovery are the right visual model for correlation display

## Decision

CorrelCore has exactly **5 primary screens**. No screen may be added without an explicit justification and a new or amended ADR.

| #   | Route                    | Purpose                                                                        |
| --- | ------------------------ | ------------------------------------------------------------------------------ |
| 1   | `/`                      | Home: daily touch point, latest insight preview, entry CTA                     |
| 2   | Bottom sheet (from Home) | Entry form: log daily entry in ≤ 60 seconds                                    |
| 3   | `/insights`              | Insights feed: all worker-generated insights with progressive disclosure       |
| 4   | `/trends`                | Trend charts: long-term mood, tag frequency, work context visualisations       |
| 5   | `/settings`              | Settings: profile, tags, symptoms, privacy, export, analytics toggle, dev mode |

The **Developer screen** (`/dev`) is a diagnostic tool, not a user-facing screen. It is accessible only after unlocking developer mode (7× tap on version string in Settings footer). See ADR-0019.

### Home Screen — streak widget removed

The `[Streak: 🔥 7]` sketch present in the previous FRONTEND.md is formally removed. The home screen information hierarchy is:

1. Date + work context badge
2. Latest insight card (best-effort, non-blocking)
3. 7-day mood sparkline
4. Primary CTA: "Log today"

Tracking consistency (neutral percentage, no streak framing) is shown only within the `FirstWeekInsightBanner` while `sample_n < 7`.

### Insight Screen — sort order and progressive disclosure

Insights are sorted by `confidence × effect_size` descending. Each card has three disclosure levels:

1. **Collapsed:** direction indicator (↗/↘), title, confidence bar, one-sentence statement
2. **Expanded:** full dual-axis chart (custom SVG), `r` value, `p` value, sample details
3. **Full detail:** data export, lag selector (future M4+)

### Navigation contract

The root `+layout.svelte` acts as the app shell and auth guard. All authenticated routes implicitly form an `(app)` group. The bottom navigation bar provides access to Home, Insights, Trends, and Settings.

## Consequences

- The `FRONTEND.md` is replaced in full (this ADR documents the reasons).
- All M3.1 issues (#160–#166) implement components within this architecture.
- Any new route proposal must reference this ADR and explain the addition.
- The `InsightMatrix.svelte` component (currently in `components/insights/`) should be evaluated against the new `InsightFeed` + `InsightCard` pattern in Sprint 7/8 and removed or repurposed if redundant.
