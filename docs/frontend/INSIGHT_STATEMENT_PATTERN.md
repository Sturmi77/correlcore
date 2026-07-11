# Insight-Statement-Pattern

Status: Proposed — design direction; synthetic sparkline removal landed
([#342](https://github.com/Sturmi77/correlcore/pull/342)), hierarchy/consolidation/
refresh proposals not yet implemented
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

## Component consolidation: one evidence primitive, not six

`InsightMaturityBadge`, `InsightConfidenceScale`, `InsightQualityMeter`,
`InsightJourneyBanner`, `InsightJourneyExplainer`, and `InsightStageHeader`
all express some variant of "how certain/mature is this" — with their own
markup, copy, and layout. This is the structural reason continuous
refinement never converges: six components each carry a piece of the same
signal, so fixing the hierarchy in one never fixes it everywhere.

Proposal: collapse these into a single **evidence row** — a tier chip +
confidence dots + sample count in one line, used identically wherever
Level-2 evidence is shown. `InsightStageHeader`'s milestone-progress copy
(distinct from per-insight evidence) is out of scope for this
consolidation and can stay separate.

## Feed prioritization: use the `featured` prop that already exists

`InsightFeed.svelte` sorts correctly via `rankInsights()` (confidence ×
|effect size|, descending) but never sets `featured` when rendering the
list (`{#each filtered as insight}<InsightCard {insight} ... />`) — it's
only used, in isolation, by `MobileInsightLead`. The ranking is already
right; it just isn't visible. Proposal: pass `featured` to `filtered[0]`
so the strongest pattern gets visibly more weight than the rest of the
list, not just a better sort position.

## Landed: synthetic sparkline removed

`InsightCard`'s expanded state rendered a chart from `sparkPoints()` —
`Math.sin(i * 2.1 + baseline * 10) * 0.18`, a decorative curve
parameterized only by `effect_size`/`sample_n`, not real historical
entries. In an app whose core promise is honest correlation work, a
fabricated trend line is a bigger risk than no chart. Removed in
[#342](https://github.com/Sturmi77/correlcore/pull/342); the confidence
scale and technical meta grid (real numbers from `InsightResponse`) are
unaffected.

## Visual refresh proposals

Five findings, each backed by a code search rather than a stylistic
opinion. All stay inside the existing `app.css` token system — no new
color palette.

1. **Metric-color identity.** `--color-metric-mood/-energy/-stress` are
   defined but used in exactly one place, `lib/utils/charts.ts` (chart
   line colors) — nowhere in card/badge/icon UI. Proposal: color an
   insight card's accent (direction glyph, left border) by
   `insight.metric` instead of a generic primary/success/error, so
   mood/energy/stress become visually distinguishable outside charts too.
2. **Use the unused top of the type scale.** `--text-xl` (up to 2.25rem)
   is the largest step of the existing scale but appears in no read
   insight/home component — everything sits between `xs` and `lg`.
   Proposal: give the featured card's statement `text-xl` instead of
   `text-lg` for a real size jump against the rest of the list, not just
   "slightly bolder."
3. **Purposeful motion.** Only 9 of 32 files in `components/insights` +
   `components/home` contain any `transition`/`animation` at all, almost
   entirely button hover states. Proposal: a short reveal (~320ms,
   existing `--transition-interactive` easing) when the featured
   statement appears, respecting `prefers-reduced-motion`.
4. **A card-elevation rule.** `InsightCard` declares
   `box-shadow: var(--shadow-sm)` and `transition: box-shadow 200ms` with
   no hover rule that ever changes it — a dead transition. Meanwhile
   `HomeDailyBrief`/`HomeInsight` use no shadow at all, and `Panel` has an
   opt-in `--elevated` modifier. Three different strategies, no visible
   rule. Proposal: interactive/tappable cards get a shadow plus a real
   hover/press state (using the already-declared hook); static info
   panels stay border-only.
5. **An icon-size scale.** Icon sizes are ad hoc across the codebase —
   `size={14}`, `16`, `18`, `20`, `22`, `40`, `72`, plus assorted
   stroke-widths — with no scale, unlike spacing or type. Proposal:
   `--icon-sm/-md/-lg` tokens, new additions alongside the existing
   `--text-*` scale (not a replacement for anything).

A first visual pass of all of the above (evidence row, featured feed
card, sparkline removal, and all five refresh proposals) has been
explored in an artifact draft outside this repo; nothing here is
implemented in `InsightFeed`, the evidence components, or `app.css` yet.

## Open questions before implementation

- Should `InsightFeed`'s featured treatment differ from `MobileInsightLead`'s,
  or should the mobile "hero" simply become "the featured card from the
  feed, shown standalone"?
- Does the evidence-row consolidation change any test IDs or props that
  `InsightStageHeader`'s milestone-only usage in `MobileInsightLead`
  depends on?
- Icon-size tokens are new (`--icon-*` doesn't exist today) — confirm
  values against the actual size distribution before introducing them,
  rather than picking three round numbers.
