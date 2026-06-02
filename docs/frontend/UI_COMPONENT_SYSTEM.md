# UI Component System - Sprint A

Status: Accepted planning contract for mobile hardening  
Last updated: 2026-05-31

## Purpose

Sprint A consolidates the current frontend controls into one shared component direction before UI refactoring starts. The goal is to make CorrelCore easier to scan, easier to operate on mobile, and less dependent on route-local styling.

This document is the target contract for the next implementation sprints. It does not claim that every primitive already exists in code.

## Current Inventory

| Area              | Current implementation                                                   | Risk                                                                         | Target owner                                        |
| ----------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------- |
| Global primitives | `.btn`, `.btn-sm`, `.input`, `.badge`, `.card` in `apps/web/src/app.css` | Mostly CSS-only; no prop API, state contract, or accessibility defaults      | `lib/components/common`                             |
| App chrome        | `AppNav`, `ThemeToggle`, route-local top links                           | Repeated Home/theme/logout controls fragment screen hierarchy                | `AppShell`, `ScreenHeader`                          |
| Home actions      | Home CTA, dismissable insight card, secondary text nav links             | Home mixes daily action, insight maturity, trend links, and analysis state   | Home route plus shared `Button`/`Panel`             |
| Insight controls  | `InsightCard`, `InsightFeed`, `InsightMatrix`, export buttons            | Advanced matrix/table behavior creates mobile overflow risk                  | Insights route plus shared tabs/panels              |
| Trend controls    | Local segmented tabs, settings link, chart range controls                | Different button styles and local state labels reduce predictability         | Trends route plus `SegmentedControl`                |
| Entry controls    | `EntrySheet`, `ScaleSlider`, `TagPicker`, quick-pick buttons             | Good touch-target basis, but labels and grid layout need 375 px verification | Entries feature plus shared form controls           |
| Settings controls | Many button variants, toggles, tag management links                      | Variant naming is inconsistent across routes                                 | Settings feature plus shared `Button`/`InlineAlert` |

## Target Component API

The implementation should converge on these shared primitives before broad visual changes.

### `Button`

Use for text buttons and icon+text actions.

Required contract:

- `variant`: `primary`, `secondary`, `ghost`, `danger`, `link`
- `size`: `sm`, `md`, `lg`
- `fullWidth`: boolean, mobile-friendly by default when used as a primary CTA
- `disabled`, `loading`, and `aria-busy` handling
- Supports `href` for link-style navigation without changing visual rules
- Minimum rendered touch target: 44 x 44 px

Variant rules:

- `primary`: one main action per screen or sheet
- `secondary`: alternate action inside the same workflow
- `ghost`: chrome, dismiss, theme, and low-emphasis actions
- `danger`: destructive or irreversible actions only
- `link`: inline text navigation only, not a card/action replacement

### `IconButton`

Use for dismiss, close, theme, help, and export affordances where the icon is the label.

Required contract:

- `ariaLabel` is required
- Tooltip text is required for unfamiliar actions
- Minimum rendered touch target: 44 x 44 px
- The icon must not be the only state indicator

### `ScreenHeader`

Use once per primary screen below the app shell.

Required contract:

- `title`, optional `subtitle`
- Optional compact action slot
- No duplicate Home button when the app navigation is visible
- Theme switching belongs in global chrome or Settings, not every route header

### `Panel`

Use for bounded information or tool surfaces.

Variants:

- `plain`: unframed page section
- `bordered`: grouped information without elevation
- `elevated`: repeated cards only
- `chart`: visualizations with fixed dimensions and responsive overflow handling
- `danger`: irreversible settings or warnings

Rules:

- Do not nest cards inside cards.
- Do not use a card for full page sections.
- Use stable dimensions for charts, counters, button rows, and fixed-format controls.

### `SegmentedControl`

Use for mutually exclusive filters such as trend range or insight category.

Required contract:

- `value`, `options`, `onChange`
- Renders as equal-width segments when there are three or fewer options
- Wraps or becomes a select-like control at 375 px instead of forcing horizontal scroll
- Active state must be visible without relying on color alone

### `TabBar`

Use for within-screen views, not for primary app navigation.

Required contract:

- Uses ARIA tab semantics when panels are switched in place
- Labels must fit at 375 px or use controlled horizontal scrolling; TabBar must not wrap filter
  pills into disjoint rows on small screens
- Primary app navigation remains owned by `AppNav`

### `BottomSheet`

Use for the entry form and secondary flows that should not become primary screens.

Required contract:

- Close button uses `IconButton`
- Focus is trapped while open
- Escape/backdrop close behavior is explicit per use case
- Sheet content must be operable at 375 px without horizontal scroll
- Sheet panels must include safe-area-aware bottom padding and avoid leaving inert backdrop space
  below actionable content on mobile devices

### `EmptyState`, `InlineAlert`, `DataState`

Use for loading, error, empty, and offline states.

Required contract:

- Every data-fetching component maps to `loading`, `error`, `empty`, `offline`, and `ready`
- Retry actions use `Button variant="secondary"`
- Offline state uses neutral copy and does not imply data loss unless confirmed

## Screen Ownership Rules

## Control Semantics

This contract is mandatory for all new and refactored route controls. A control's
visual style must match its meaning, not merely its local layout.

| Control            | Use for                                                                                    | Do not use for                                          |
| ------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| `TabBar`           | Switching in-screen views such as Findings/Matrix or Compare/Health/Habits                 | Filters, layer toggles, primary app navigation          |
| `SegmentedControl` | One exclusive value such as range, smoothing mode, language, or a short mode selector      | Multi-select metrics or independent visibility toggles  |
| Checkbox / switch  | Independent layers, persistent settings, or multi-select metric visibility                 | Navigation or mutually exclusive views                  |
| Chips              | Fast content selection inside entry/input flows, especially tags, symptoms, and time slots | Screen navigation or analysis view switching            |
| `Button`           | Actions, links that behave as actions, and primary/secondary CTAs                          | Passive status, placeholders, or selected state display |
| `IconButton`       | Close, dismiss, help, info, export, and other compact tool actions                         | Unknown actions without labels/tooltips                 |
| `Panel`            | One bounded information or tool surface                                                    | Nested cards or full-page section decoration            |

Mobile-first hierarchy rule: after the screen header and at most one compact
status/control row, the first viewport must show the screen's main value:
content, a chart, the entry form, or a compact actionable empty state. A mobile
viewport should never be consumed only by headings, readiness cards, and control
rows.

Route-local button groups, tab groups, view toggles, and disabled placeholder
buttons are legacy. Replace them with the shared primitives above when touching
the route.

### Home

Home is the daily touch point. It owns:

- Date/work context summary
- Latest best-effort insight or first-week state
- Seven-day mood sparkline
- Primary daily entry CTA

Home must not own:

- Insight maturity journey banners
- Phase milestone cards
- Insight matrices
- Deep filters
- Secondary text navigation that duplicates app navigation
- Streak or chain counters

### Insights

Insights owns:

- Full insight feed
- Progressive disclosure for insight details
- Insight maturity and phase context
- Advanced matrix/export controls, preferably below the feed or behind an explicit advanced panel

### Trends

Trends owns:

- Metric history
- Entry history sheets
- Tracking consistency as a neutral rate
- Time range and metric filters

Avoid streak framing even when backend fields are currently named `current_streak` or `longest_streak`.

### Settings

Settings owns:

- Theme and language preferences
- Logout/account controls
- Data export and destructive account actions
- Tag management entry points

## Mobile Hardening Rules

- Design at 375 px first, then confirm 768 px and 1024 px.
- No horizontal page scroll at 375 px.
- Horizontal overflow is allowed only for charts or data tables with an explicit affordance and a non-table fallback when practical.
- Labels in buttons, tabs, sliders, and chips must wrap or shorten before they overflow.
- Within-screen tab sets may use horizontal scrolling when labels would otherwise wrap poorly.
- Header actions collapse before content does.
- Dense data matrices must keep axis labels visually attached to their cells. At 375 px, prefer a
  local chart/table scroller with compact horizontal labels over rotated labels that overlap cells.
- Repeated controls must use the shared component API before route-specific styling is added.

## Migration Backlog

1. Done in Sprint B: add initial `Button` and `IconButton` primitives under `apps/web/src/lib/components/common`.
2. In progress from Sprint B onward: replace route-local primary/secondary/ghost button classes with `Button` and `IconButton`; remaining route-local classes stay tracked as a [M4 mobile-hardening](../DESIGN_DOCUMENT.md#m4--mobile-polish--pwa-hardening-woche-1112) follow-up.
3. Done in Sprint C: replace repeated route headers with `ScreenHeader` on Insights, Trends, Settings, and Tag Settings.
4. Done in Sprint D: replace Trends range filters and Trends/Insights tabs with `SegmentedControl` and `TabBar`.
5. Done in Sprint E: add `Panel`, `InlineAlert`, `EmptyState`, and `DataState`; migrate InsightFeed states and simple auth/loading/error panels on Insights, Trends, Settings, and Tag Settings.
6. Done in Sprint B: normalize Home to the owned daily touch-point elements and remove duplicate secondary navigation.
7. Done in Sprint B for Home: keep maturity journey and phase context off Home; Insights remains the owner.
8. Next: add mobile screenshot checks for Home, Entry Sheet, Insights, Trends, and Settings at 375 px; target [M4 mobile-hardening](../DESIGN_DOCUMENT.md#m4--mobile-polish--pwa-hardening-woche-1112).
9. Next: add a style contract test or lint rule that flags unknown design-token and variant names; target [M9 beta hardening](../DESIGN_DOCUMENT.md#m9--beta-h%C3%A4rtung-woche-2224).

## Acceptance Criteria

- Every new interactive control uses a shared primitive or documents why it cannot.
- No primary screen has more than one visual primary CTA.
- Home contains no advanced analysis controls.
- Every screen renders without horizontal page scroll at 375 px.
- Common states are represented by `DataState`, `EmptyState`, or `InlineAlert`.
- `FRONTEND.md` and this document describe the same component ownership model.
