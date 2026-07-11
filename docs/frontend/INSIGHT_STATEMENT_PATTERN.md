# Insight-Statement-Pattern

Status: Proposed — design direction, not yet implemented
Last updated: 2026-07-11

## Purpose

CorrelCore's core value proposition is explaining _why_ days were good or bad —
"Zusammenhänge statt Rohdaten" (DESIGN_DOCUMENT.md §1.4). The backend already
generates clear, human-readable sentences for this (`Insight.statement`, see
`backend/app/services/insight_engine.py`), for example:

> "Days tagged Homeoffice currently line up with lower mood scores in your
> data. Treat this as a pattern to reflect on, not a cause."

An audit of the four places that render insights (`InsightCard`,
`InsightFeed`, `HomeDailyBrief`, `MobileInsightLead`) found that this
sentence is consistently present but visually subordinate — every surface
gives more visual weight to a compressed technical label (e.g.
`mood_score → Homeoffice`, built by `InsightCard.buildTitle()`, or
`latestInsight.subject_label ?? latestInsight.metric` in
`HomeDailyBrief.daily-brief__title`) than to the sentence itself. The
sentence renders smaller and/or muted, competing with badges, meta rows, and
(in `HomeDailyBrief`, fixed separately) a redundant second copy of itself.

This document defines a shared hierarchy so all four surfaces present the
same insight consistently, instead of four different interpretations of the
same data model.

## Core principle

**An insight has exactly one primary representation: the sentence
(`statement`). Everything else is supporting evidence, not the message.**

## The three levels

| Level                            | Content                                                                                                  | Treatment                                                                                                                     |
| -------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **0 — Always visible, dominant** | `insight.statement`                                                                                      | Largest text in the element, full text color (not muted), never truncated, no other bold/large element competes on this level |
| **1 — Secondary, supporting**    | Direction (↗/↘/→), confidence as a compact visual signal (not a raw number)                              | Smaller, as an icon/color accent beside or before the statement — never its own line with its own weight                      |
| **2 — On demand only**           | Technical label (`mood_score → Homeoffice`), sample N, tier/maturity badge, effect size, disclaimer link | Only in the expanded/detail state, or as a small, muted caption — never an `<h2>`/`<h3>`                                      |

Target layout (collapsed state):

```
[→]  Days tagged Homeoffice currently line up with lower mood scores      ← Level 0
     in your data. Treat this as a pattern to reflect on, not a cause.       (large, full color)

     mood → Homeoffice · 90 days · 34 entries                             ← Level 2
                                                                               (small, muted, one line)
```

Instead of the current:

```
mood_score → Homeoffice                                                    ← bold, large (wrong: Level 2 as Level 0)
[Badge: Preliminary]
Days tagged Homeoffice currently line up with lower mood scores...        ← small, muted (wrong: Level 0 as Level 2)
34 entries · 90 days
ⓘ What does this mean?
▼ Show more
```

## Application per component

**`InsightCard.svelte`**

- `insight.statement` becomes the first, largest text element in the header
  (replacing `buildTitle()` in that role).
- `buildTitle()`'s result becomes a small caption below the statement, or is
  dropped in favor of a metric icon/color (mood/energy/stress already have
  dedicated tokens: `--color-metric-mood` etc.).
- `MaturityBadge` moves out of the header into the meta row (Level 2) —
  no longer its own block above the statement.
- The expand/detail section (confidence scale, sparkline, technical `<dl>`)
  keeps its current structure — that remains the right place for this
  information.

**`InsightFeed.svelte`**

- Actually use the existing `featured` prop: the first item of the
  already-correct `rankInsights()` ordering gets `featured` (more weight,
  more whitespace); the rest stay compact. The ranking is already right —
  it just isn't visually expressed.

**`HomeDailyBrief.svelte`**

- `.daily-brief__title` (currently `subject_label ?? metric`, the largest/
  boldest text) and `.daily-brief__statement` (currently small/muted) swap
  weight: the statement becomes the `h2`-level line, the label becomes a
  Level-2 caption or is dropped.
- The duplicate "Top Insight" box has already been removed (see the
  `topInsight === latestInsight` fix landed alongside this document) — no
  further action needed there beyond the hierarchy swap above.

**`MobileInsightLead.svelte`**

- Inherits the fix automatically once `InsightCard` is updated. The eyebrow
  ("Insights") and heading ("Strongest pattern") stay as framing — they
  label the _context_, not the insight itself.

## Explicitly out of scope

- Color palette, tokens, dark/light theme, type scale — no token changes
  needed, only which content maps to which existing text size.
- The `InsightResponse` data model / `statement` field — the backend
  already produces good sentences; no API change required.
- No-gamification principle, disclaimer requirements, confounder notes —
  remain functionally intact, just relocated to Level 2.

## Open questions before implementation

- Should `InsightFeed`'s featured treatment differ from `MobileInsightLead`'s,
  or should the mobile "hero" simply become "the featured card from the
  feed, shown standalone"?
- Confidence as a Level-1 visual signal (color/glyph) still needs a concrete
  design — a first visual draft is being explored separately.
