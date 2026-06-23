# Mobile/Web Frontend Audit

**Date:** 2026-06-22
**Direction:** Mobile daily use first; web analysis first
**Figma:** [Audit overview](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=31-1089)

## Executive findings

1. **Mobile Trends is red.** The current chart, heatmap, cursor, and comparison
   interactions cannot be reduced to 390 px without losing comprehension.
   Mobile needs ranked summaries and focused drill-down sheets rather than full
   desktop chart parity.
2. **Insights has the largest design/code gap.** `InsightFeed`, `InsightCard`,
   `InsightMatrix`, quality/confidence surfaces, and co-occurrence views are
   implemented in code but incompletely represented in Figma.
3. **Entry is the highest-frequency mobile risk.** `EntryForm`, `TagPicker`,
   `SymptomChecker`, save state, validation, and offline behaviour must work
   together without making daily capture dense or fragile.
4. **The shell split is valid and already partially implemented.** The global
   CSS switches bottom navigation to a desktop rail at 768 px, but route-level
   desktop composition remains inconsistent.
5. **Settings, auth/onboarding, and offline/PWA lack current Figma coverage.**
   These omissions hide important error, verification, install, and recovery
   states.
6. **A separate mobile codebase is not justified.** ADR-0002 and the current
   SvelteKit/Capacitor strategy favour shared domain logic and route semantics.

## Screen matrix

| Screen            | Mobile | Web    | Primary problem                                     | Decision                                                                                      |
| ----------------- | ------ | ------ | --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Home / Today      | Yellow | Green  | Figma covers only part of the real home composition | Keep mobile as Daily Brief; expand desktop context without turning Home into a control centre |
| Entry             | Yellow | Yellow | Form density and incomplete state coverage          | Mobile capture flow first; desktop workspace second, shared model and validation              |
| Trends            | Red    | Green  | Dense chart interaction                             | Desktop is primary; mobile gets summaries and drill-down sheets                               |
| Insights          | Red    | Yellow | Real insight components missing from Figma          | Define feed/card/quality variants before implementation alignment                             |
| Settings          | Yellow | Green  | Missing Figma flow                                  | Mobile essentials; full web management surface                                                |
| Auth / Onboarding | Yellow | Yellow | Missing conversion and verification states          | Add responsive form, error, success, and verification specs                                   |
| Offline / PWA     | Yellow | Yellow | Missing recovery states                             | Specify offline, install, update, pending-sync, and retry states                              |

## Component findings

### Mobile-critical

- `EntryForm`: split composition while preserving one data contract.
- `TagPicker`: define overflow, category, create-tag, limit, and error states.
- `SymptomChecker`: add Figma coverage and mobile progressive disclosure.
- `ScaleSlider`: verify 44 px controls, value feedback, keyboard support, and
  long translated labels.

### Web-primary

- `MetricTimeseries`, `ComparisonHeatmap`, `TrendsComparePanel`,
  `UnifiedStripChart`, `TagHeatmap`, and `HabitsPanel` retain their full
  analytical form on desktop.
- Mobile equivalents communicate top signals and open focused details; they do
  not render the complete desktop visualisation at reduced scale.

### Missing design-system coverage

- `InsightFeed`, `InsightCard`, `InsightMatrix`,
  `InsightQualityMeter`, `SymptomChecker`, settings management, auth,
  onboarding, and offline/PWA states.

## Conflicts and constraints

- The five-screen architecture from ADR-0017 must remain intact.
- Home must remain a Daily Brief, consistent with the M5 streamline amendment.
- Trends must remain mobile-friendly as required by `DESIGN_DOCUMENT.md`;
  this means simplification, not dashboard compression.
- Capacitor must reuse the SvelteKit codebase; platform-specific code is limited
  to native capabilities and shell integration.
- Code Connect is unavailable until Figma has an eligible Organization or
  Enterprise Dev/Full seat. The repository mappings remain the handoff source.

## Evidence

- Machine-readable matrix:
  [`apps/web/figma/mobile-web-audit.json`](../../apps/web/figma/mobile-web-audit.json)
- Figma node ledger:
  [`apps/web/figma/correlcore-figma-map.json`](../../apps/web/figma/correlcore-figma-map.json)
- Existing responsive breakpoint:
  `apps/web/src/app.css` at `@media (min-width: 768px)`.
