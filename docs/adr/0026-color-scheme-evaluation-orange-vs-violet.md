# ADR-0026 – Color Scheme Evaluation: Orange/Dark vs. Violet/Dark

## Status

Accepted (2026-05-26)

## Context

A structured color-scheme evaluation was conducted to determine whether a
Black / Dark-Grey / Orange palette (inspired by Grafana, Home Assistant)
could serve CorrelCore better than the violet baseline established in ADR-0020.

The evaluation was triggered because ADR-0020 was made without a formal
theoretical framework: no WCAG contrast tables for both modes, no competitive
analysis of palette overlap, and no documented color-semantic rationale.

The full theoretical framework, contrast tables, and design rationale are
in `docs/frontend/COLOR_SCHEME_CONCEPT.md`.

The evaluation covered:

- Color theory (hue semantics, simultaneous contrast, Bezold effect)
- WCAG 2.2 contrast ratios in dark AND light mode
- Cognitive associations for the privacy-first selfhoster audience
- Competitive landscape (Grafana, Home Assistant, Nextcloud)
- Codebase alignment with `apps/web/src/app.css`

## Decision

**The orange/dark palette is rejected as primary identity. Violet/dark is
confirmed per ADR-0020.**

### Why orange was considered

| Argument                                                   | Assessment                                               |
| ---------------------------------------------------------- | -------------------------------------------------------- |
| Selfhoster ecosystem recognition (Grafana, Home Assistant) | Valid — target audience familiarity is high              |
| High-energy, activating hue                                | Counterproductive for a passive, reflective tracking app |
| Distinct market positioning                                | Undermined by visual sameness with Grafana               |

### Rejection reasons

1. **WCAG light-mode failure**: `#E8922A` achieves ~2.5:1 on `#fafaf7`
   — below WCAG AA (4.5:1). A split accent (`#B85F10` in light mode) would
   be required, fragmenting brand identity across modes.

2. **Semantic mismatch**: Orange signals urgency and action. CorrelCore is a
   reflective, ambient-awareness tool. The hue creates cognitive dissonance
   with the product's core promise of introspection and pattern discovery.

3. **No market differentiation**: The palette is visually identical to Grafana
   and Home Assistant. CorrelCore is not a monitoring tool — it should not
   look like one.

4. **Token architecture cost**: A full orange rebrand invalidates all existing
   semantic tokens in `app.css` (ADR-0020) for zero user-facing value.

5. **Surface color complexity**: Warm-dark surfaces (`#171614`) already solve
   OLED halation and simultaneous-contrast problems correctly without requiring
   an orange accent to anchor the palette.

### Why violet/dark is confirmed

- Violet is cognitively associated with introspection, depth, and pattern
  recognition — a strong semantic fit for a correlation analysis tool.
- The current token architecture is complete, WCAG-compliant in both modes,
  and production-tested.
- Violet is visually rare in the selfhosting/analytics space — genuine
  differentiation against Grafana (orange), Nextcloud (blue), Home Assistant
  (teal/orange).
- Heatmap tokens use a neutral blue scale, ensuring data encoding independence
  from the primary brand color.
- The existing `[data-theme='dark']` and `[data-theme='light']` token blocks
  already satisfy WCAG AA in both modes without modification.

## Consequences

- No color palette change to primary identity.
- ADR-0020 remains canonical for primary color tokens.
- Future ADRs may introduce an **optional orange secondary accent** for
  specific high-urgency CTA contexts (e.g., overdue reminders, destructive
  action warnings) — only as a semantic status color, never as primary brand
  color.
- The `--color-ms-primary*` legacy aliases in `app.css` must be removed
  during the M3.7 color hardening sprint (Sprint 1).
- `docs/frontend/COLOR_SCHEME_CONCEPT.md` is the reference for all future
  palette discussions.
- ADR-0027 formally specifies light mode color requirements that were missing
  from ADR-0020.

## References

- [ADR-0020](0020-primary-color-system.md): Primary Color System
- [ADR-0027](0027-light-mode-color-requirements.md): Light Mode Requirements
- `docs/frontend/COLOR_SCHEME_CONCEPT.md`: Full theoretical framework
- `apps/web/src/app.css`: Runtime token source
- WCAG 2.2 SC 1.4.3 (Contrast Minimum)
- WCAG 2.2 SC 1.4.11 (Non-text Contrast)
