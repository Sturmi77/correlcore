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

## 2026-05-29 M5 Streamline Amendment

The five-screen architecture remains canonical. M5 frontend streamlining may move data out of the default viewport, but must not remove data depth:

- Home becomes a Daily Brief, not a mini-dashboard. Deep filters, matrices, and raw values live in Insights or Trends drilldowns.
- Insights shows exactly one phase/readiness surface via `InsightStageHeader`; the matrix remains a secondary drilldown inside `/insights`.
- Trends becomes Compare-first: metric lines and tag/symptom heatmap rows share one time axis. `Activities` is represented as tag rows in Compare instead of a default tab.
- Symptom heatmap in M5 is neutral occurrence/intensity visualization only. It does not introduce symptom co-occurrence, medical interpretation, correlation recommendations, or a new analytics engine.
- Desktop layouts may use split views, side panels, and sticky controls. These are secondary surfaces inside existing routes, not new primary screens.

## 2026-06-22 Mobile/Web Composition Amendment

The five-screen architecture remains unchanged. Mobile and desktop are
presentation roles within the same SvelteKit route and domain architecture:

- Mobile is the daily-use surface for capture, check-in, concise feedback, and
  focused drill-downs.
- Desktop is the analysis and management surface for comparison, dense
  visualisation, and administration.
- Trends may not compress the full desktop dashboard into a mobile viewport;
  it exposes shared analytics through summaries and focused detail states.
- Entry may use different mobile and desktop composition, but validation,
  persistence, and route semantics remain shared.
- A separate mobile frontend codebase requires a new ADR. Capacitor continues
  to wrap the shared SvelteKit application.

The current derived specification is [`../FRONTEND.md`](../FRONTEND.md).
Findings and delivery order are documented in
[`../frontend/MOBILE_WEB_AUDIT.md`](../frontend/MOBILE_WEB_AUDIT.md) and
[`../frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](../frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md).

## 2026-07-31 Configurable Home Sections Amendment (#584)

The five-screen architecture remains unchanged. Home (`/`) stays a daily touch
point — not a mini-dashboard. Users may optionally reorder or hide compact
information blocks stored in `user_preferences.home_sections`.

**Fixed elements (not configurable):**

- Today context strip (`HomeTodayContext`) — always first
- Primary entry CTA when today is not logged
- PWA install banner and onboarding redirect gating

**Configurable sections (default order matches M3.5 brief-first layout):**

1. `first_week_banner` — early context insight banner
2. `daily_brief` — insight/phase summary and bridge links to Insights/Trends
3. `work_context` — work-context pattern bars
4. `weekday_overview` — weekday mood strip and top signals

`NULL` or empty stored preferences resolve to the default layout so existing
users see no change until they customize. New section keys merge into defaults
without breaking saved order. Deep filters, matrices, sparklines, and recent-entry
grids remain off Home regardless of customization.

Settings live at `/settings/home` (secondary surface within the Settings screen,
not a new primary screen). See
[`../proposals/FEATURE_HOME_SCREEN_CUSTOMIZATION.md`](../proposals/FEATURE_HOME_SCREEN_CUSTOMIZATION.md).

## 2026-08-24 Unified Screen Chrome / Header Contract Amendment (#703)

There is one shared top-chrome contract: every primary and drill-down screen
renders exactly one `ScreenHeader`, never a hand-rolled `__top` bar or raw `btn`
back anchor.

**Grammar:** `[back/context] · [title] · [controls/actions]`.

- **Back / context** — every drill-down screen passes `back={{ href, label }}`
  and `ScreenHeader` renders the single shared ghost link (left of the title,
  labelled with the destination): all settings sub-pages, the insights
  drill-downs (`digest`, `history`), `/health-connect`, `/dev`, `/admin`, and
  `/entries/day`. No route hand-rolls a `__top` bar, a raw anchor, or a
  `slot="actions"` back button. _Exception:_ the dual-origin legal pages
  (`/impressum`, `/privacy`) keep in-body back buttons for both the app and the
  public landing footer.
- **Theme** — `ThemeToggle` lives only on `settings/appearance` and is not part
  of route or drill-down headers. _Exception:_ the full-page entry form
  (`EntryForm` `mode === 'page'`) keeps one, as a focused input surface with no
  header/nav chrome of its own.
- **Floating header (Stage 2)** — screens that carry controls (Trends, Insights)
  set `sticky`. The header is then the sticky screen chrome (blur/backdrop, owns
  the top offset via `position: sticky`, so no separate `--app-header-height`
  fixed-bar offset is needed), and the analysis toolbars render inside its
  `controls` slot instead of positioning themselves sticky. The title copy
  collapses on scroll (`prefers-reduced-motion` respected) so `[back · controls]`
  stays reachable without a tall fixed header eating the ~640px content shell.
- **Out of scope** — `visuallyHidden` screens (Home, Onboarding) keep no visible
  header and are never made sticky.

Consistent with the Mobile/Web Composition amendment: one responsive component
(mobile-lean/collapsing, desktop-richer inline), not a separate desktop header.
Enforced by `src/routes/screen-chrome.test.ts` and
`src/routes/control-primitives.test.ts`.
