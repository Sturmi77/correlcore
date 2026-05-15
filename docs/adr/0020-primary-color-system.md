# ADR-0020 - Primary Color System for M3.5 Frontend

## Status

Accepted (2026-05-15)

## Context

The pre-M3.5 frontend still used the earlier teal primary color tokens. During
the M3.5 design review, `docs/FRONTEND.md` defined a more analytical visual
direction for CorrelCore: neutral surfaces, custom SVG charts, and a violet
primary color. That direction better supports the product position as a
privacy-first correlation analysis tool rather than a playful wellness journal.

Keeping teal in `app.css` while documenting violet in `FRONTEND.md` creates
drift across components, screenshots, QA criteria, and future M3.5 issues.

## Decision

CorrelCore adopts violet as the canonical primary color family for the web
frontend:

| Token                       | Dark      | Light     |
| --------------------------- | --------- | --------- |
| `--color-primary`           | `#7c6af5` | `#6356d9` |
| `--color-primary-hover`     | `#9587ff` | `#5548c5` |
| `--color-primary-active`    | `#6a5be0` | `#4338a8` |
| `--color-primary-highlight` | `#2b2742` | `#ebe9ff` |

The legacy `--color-ms-primary*` aliases remain temporarily mapped to the
light-mode violet values so older components do not regress while M3.5 removes
remaining legacy token usage.

Heatmap tokens are kept separate from the primary color and use a neutral blue
scale. Calendar and frequency charts must not use red/green traffic-light
coloring because that implies a behavioural verdict and conflicts with the
no-gamification promise.

## Consequences

- `apps/web/src/app.css` is the runtime source of truth for theme tokens.
- `docs/FRONTEND.md` is no longer pending a color ADR; this ADR is the formal
  reference.
- Browser theme colors in `apps/web/src/app.html` use the same primary/dark
  foundation.
- Future components must use semantic tokens (`--color-primary`,
  `--color-primary-highlight`, `--color-heatmap-*`) instead of hardcoded teal
  or `rgb(var(--color-primary-500...))` fallbacks.
- Remaining legacy color references should be cleaned up incrementally during
  the M3.5 screen sprints.
