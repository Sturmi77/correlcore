# ADR-0018 — Insight Confidence Visualisation

## Status

> ⚠️ **Superseded by [ADR-0021](./0021-insight-maturity-phases.md)** (2026-05-16)
>
> The `InsightConfidenceScale` component and its 0–1 confidence mapping are replaced by the
> `InsightMaturityBadge` and the four-phase maturity model. Raw confidence scores are no longer
> shown to the user. See ADR-0021 and `docs/frontend/INSIGHT_MATURITY.md` for the new spec.

~~Accepted (2026-05-13)~~

---

## Context

The analytics engine produces an `insight.confidence` float (0.0–1.0) and `insight.sample_n` integer for every generated insight. These values must be communicated to the user. Three options were evaluated:

**Option A — Dot indicators (●●●●○):**

- 5 discrete levels, immediately readable
- Low cognitive load
- Risk: aesthetic association with star ratings / gamification

**Option B — Percentage bar with numeric label (73%):**

- Continuous, technically precise
- Problem: "73%" reads as "almost certain" in everyday language, but on 30–60 data points a 0.73 confidence is only a moderate finding — pseudo-precision that the model does not support
- Problem: a filled bar visually resembles a progress bar / achievement unlock (implicit gamification)

**Option C — Single-colour labelled progress bar (chosen at the time):**

- Bar width encodes relative strength visually (technical feel)
- A semantic label replaces the numeric percentage on the card surface
- Raw `confidence` float and `sample_n` are shown in the expanded state only
- No percentage is shown on the collapsed card — avoids pseudo-precision
- Bar uses `--color-primary` at increasing opacity (single hue)

## Decision (original — now superseded)

Option C was adopted. The `InsightConfidenceScale` component was specified to implement this.

## Why Superseded

ADR-0021 identified that a single confidence indicator is insufficient because it says nothing about
**data maturity**. A 0.73 confidence on 8 entries means something entirely different from 0.73 on 80 entries.
The phase model in ADR-0021 surfaces this distinction explicitly, making `InsightConfidenceScale`
misleading in early phases.

The `InsightMaturityBadge` component replaces it with a phase + entry count label that is always
contextually honest about the strength of the underlying evidence.

## Consequences (historical)

- `InsightConfidenceScale.svelte` — superseded; replace with `InsightMaturityBadge.svelte`
- `InsightCardExpanded.svelte` — raw confidence float may still be shown in developer/debug mode only
- Issues #161 and #162 are closed/updated in favour of issues from ADR-0021
