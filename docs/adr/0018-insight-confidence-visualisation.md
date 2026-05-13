# ADR-0018 — Insight Confidence Visualisation

## Status

Accepted (2026-05-13)

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

**Option C — Single-colour labelled progress bar (chosen):**
- Bar width encodes relative strength visually (technical feel)
- A semantic label replaces the numeric percentage on the card surface (`Early signal` / `Emerging pattern` / `Moderate finding` / `Strong finding` / `Very strong finding`)
- Raw `confidence` float and `sample_n` are shown in the expanded state only (Level 2 / Level 3 disclosure)
- No percentage is shown on the collapsed card — avoids pseudo-precision
- Bar uses `--color-primary` at increasing opacity (single hue) — never red/green traffic-light colours

## Decision

Option C is adopted. The `InsightConfidenceScale` component (already present in `components/home/`) is extended to implement this specification.

### Mapping table

| confidence range | bar fill | label |
|---|---|---|
| 0.0–0.2 | 20% | Early signal |
| 0.2–0.4 | 40% | Emerging pattern |
| 0.4–0.6 | 60% | Moderate finding |
| 0.6–0.8 | 80% | Strong finding |
| 0.8–1.0 | 100% | Very strong finding |

### Accessibility requirement

The bar element must carry `role="meter"` with `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="1"`, and `aria-label` containing the semantic label text. Colour is never the only information carrier (WCAG 1.4.1).

## Consequences

- `InsightConfidenceScale.svelte` must be updated to match this spec (Issue #161).
- The expanded insight state (`InsightCardExpanded.svelte`, to be created in Issue #162) shows the raw `confidence` value and `sample_n` as plain numeric metadata.
- The existing `InsightConfidenceScale.test.ts` must be extended to cover all 5 label mappings and the ARIA attributes.
- Stars, dots (●●●●○), and raw percentage displays on collapsed cards are formally ruled out.
