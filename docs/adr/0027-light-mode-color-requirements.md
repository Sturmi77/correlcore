# ADR-0027 – Light Mode Color Requirements

## Status

Accepted (2026-05-26)

## Context

The light mode token block in `apps/web/src/app.css` exists and functions,
but there is no formal specification of its requirements or constraints.
ADR-0020 established the primary color tokens but did not document light-mode
contrast ratios, hard rules, or a QA gate.

Without a written spec, individual contributors must rediscover the constraints
ad hoc, which risks introducing WCAG violations or inconsistent token usage
across sprints.

Additionally, the color scheme evaluation (ADR-0026) revealed that any
alternative accent color (e.g., orange `#E8922A`) would fail WCAG AA in light
mode on the current background `#fafaf7`, confirming the need for a formal
light-mode specification.

## Decision

The following requirements are formally accepted as constraints for all
present and future light mode implementations in CorrelCore.

### Current Light Mode Token Baseline

| Token | Value | Role |
|-------|-------|------|
| `--color-bg` | `#fafaf7` | Page background (warm off-white, not pure white) |
| `--color-surface` | `#f0ede8` | Card / elevated surface |
| `--color-border` | `#d6d0c8` | Dividers, input borders |
| `--color-text` | `#1c1a17` | Primary text |
| `--color-text-muted` | `#6b6660` | Secondary / descriptive text |
| `--color-text-faint` | `#a8a39c` | Placeholder, disabled states only |
| `--color-primary` | `#6356d9` | Interactive elements, focus rings |
| `--color-primary-hover` | `#5548c5` | Hover state |
| `--color-primary-active` | `#4338a8` | Active / pressed state |
| `--color-primary-highlight` | `#ebe9ff` | Subtle tint backgrounds |

### Contrast Requirements (WCAG 2.2)

| Token pair | Minimum ratio required | Actual ratio | Status |
|------------|----------------------|--------------|--------|
| `--color-text` on `--color-bg` (`#1c1a17` / `#fafaf7`) | 4.5:1 (AA) | 16.8:1 | ✅ AAA |
| `--color-primary` on `--color-bg` (`#6356d9` / `#fafaf7`) | 4.5:1 (AA) | 5.2:1 | ✅ AA |
| `--color-text-muted` on `--color-bg` (`#6b6660` / `#fafaf7`) | 4.5:1 (AA) | 5.1:1 | ✅ AA |
| `--color-text-faint` on `--color-bg` (`#a8a39c` / `#fafaf7`) | Decorative only | 2.7:1 | ⚠️ Decorative use only |
| `--color-primary` focus ring on `--color-surface` | 3:1 (SC 1.4.11) | 4.8:1 | ✅ Pass |

### Hard Rules for Light Mode

1. **No pure white (`#ffffff`) as page background.** Use `#fafaf7` (warm
   off-white) to reduce simultaneous contrast fatigue and align with the
   warm-neutral surface language of the dark mode (`#171614` base).

2. **`--color-primary` must not be lightened in light mode.** The current
   `#6356d9` already satisfies WCAG AA at 5.2:1. Lighter violets (e.g.,
   `#8b7ef7`) drop below the 4.5:1 threshold.

3. **`--color-text-faint` is decorative-only.** It may be used for
   placeholder text, disabled input states, and purely decorative dividers,
   but never for informational content, labels, or data values.

4. **Status colors must use darkened variants in light mode.** The pattern
   already established (e.g., `#16a34a` for success, not `#4ade80`) must be
   maintained for any new status tokens. Light-mode status colors must
   individually satisfy WCAG AA against `--color-bg` and `--color-surface`.

5. **`color-scheme: light` must be declared** on the `[data-theme='light']`
   block to ensure native form controls, scrollbars, and browser chrome adopt
   light styling. This is already implemented in `app.css`.

6. **Heatmap colors require a separate light-mode contrast check.** The
   heatmap scale (`--color-heatmap-*`) must be verified against
   `--color-surface` backgrounds when used as chart fill colors (not just
   against `--color-bg`).

7. **No alternative accent color may be used as primary in light mode.** Any
   candidate accent must independently pass WCAG AA (4.5:1) on both
   `--color-bg` and `--color-surface` before being considered. Orange
   `#E8922A` fails this requirement (2.5:1 on `#fafaf7`) and is excluded as
   a primary accent per ADR-0026.

### Light Mode QA Gate

Every PR touching components or tokens must verify:

- [ ] All text/background token pairs used in the PR meet WCAG AA (4.5:1)
- [ ] Interactive elements (buttons, links) meet WCAG AA for their label text
- [ ] Focus rings (`--color-primary` outline, `3px solid`) are visible against
      both `--color-bg` and `--color-surface`
- [ ] Charts and data visualizations are legible without relying solely on color
      (dash patterns and point shapes per D-002)
- [ ] No hardcoded hex or RGB values — only semantic tokens from `app.css`
- [ ] `--color-text-faint` is used only for decorative/placeholder content

## Consequences

- This ADR is the reference document for light mode review comments in PRs.
  Reviewers may close WCAG discussions by linking to this ADR.
- All new semantic tokens must document their light-mode value and measured
  contrast ratio in the PR description before merge.
- The missing `--color-gold` token required by issue #189 (InsightMaturityBadge)
  must be added with verified dark and light mode values before that issue
  can close. Suggested values: dark `#fbbf24`, light `#b45309` (4.9:1 on
  `#fafaf7`).
- The system-preference fallback block (`@media (prefers-color-scheme: dark)`
  in `app.css`) must mirror the `[data-theme='dark']` block completely,
  including `--color-metric-*` tokens currently missing from it.
- `docs/FRONTEND.md` should link to this ADR in its theming section.
- M3.7 Sprint 2 adds `pnpm check:contrast` as a CI gate that asserts these
  ratios programmatically.

## References

- [ADR-0020](0020-primary-color-system.md): Primary Color System
- [ADR-0026](0026-color-scheme-evaluation-orange-vs-violet.md): Orange/Dark evaluation
- `docs/frontend/COLOR_SCHEME_CONCEPT.md`: Theoretical framework
- `apps/web/src/app.css`: Runtime token source
- Issue #189: InsightMaturityBadge (`--color-gold` gap)
- WCAG 2.2 SC 1.4.3 (Contrast Minimum)
- WCAG 2.2 SC 1.4.11 (Non-text Contrast)
