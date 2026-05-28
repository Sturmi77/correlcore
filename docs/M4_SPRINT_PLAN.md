# M4 Sprint Plan — Mobile/PWA Hardening + Product Insights

Last updated: 2026-05-28

This document incorporates seven product insights raised before the M4
kick-off and maps them to focused sprints. Each sprint targets a single
merge-ready PR on `main`. Sprints must be executed in order to avoid
parallel dependency conflicts.

## Background

M3.5 through M3.7 deliver a complete mobile-optimised frontend, insight
maturity phases, and a hardened color token system. M4 builds on that
foundation with four categories of work:

1. **Entry model extension** — optional time slots and cycle day field
2. **Visualisation improvements** — trend smoothing toggle
3. **Onboarding** — guided tag setup with a suggestion library
4. **Developer UX** — phase switcher and onboarding mock in Dev Mode
5. **PWA hardening** — install prompt and offline improvements
6. **Future-scoped** — co-occurrence heatmap deferred to M5

## Milestone Overview

| Sprint | Title                                            | Status  |
| ------ | ------------------------------------------------ | ------- |
| 0      | ADR & Scope Documentation                        | Pending |
| 1      | Entry Time Slots + Trend Smoothing               | Pending |
| 2      | Guided Onboarding + Cycle Tracking Groundwork    | Pending |
| 3      | Developer Mode: Phase Switcher + Onboarding Mock | Pending |
| 4      | PWA Hardening + Homescreen Install Prompt        | Pending |
| 5      | Visual QA, Docs & GitHub Closure                 | Pending |

## Deferred to Later Milestones

| Feature                           | Target | Rationale                                                        |
| --------------------------------- | ------ | ---------------------------------------------------------------- |
| Co-occurrence heatmap (Tag × Tag) | M5     | Requires a sufficient data foundation and a new backend endpoint |
| Cycle tracking deep integration   | M7     | Health Connect (Android) context; avoid premature health claims  |
| Pattern recognition / clustering  | M8     | Needs pgvector and statistically robust data volume              |
| Native Android homescreen widget  | M11    | Depends on Play Store / TWA path; Glance API                     |

---

## Sprint 0 — ADR & Scope Documentation

**Goal:** Document all architectural decisions introduced in M4 before
implementation begins. No code changes.

### Deliverables

- [ ] `docs/adr/0028-entry-time-slot-model.md`
  - Decision: optional `time_slot` enum (`morning | noon | evening | null`) on
    the `DayEntry` model; `null` means whole-day entry (backward compatible)
  - Migration strategy: additive Alembic migration, no existing data touched
- [ ] `docs/adr/0029-trend-smoothing-frontend.md`
  - Decision: 7-day simple moving average computed client-side in Recharts;
    no new backend endpoint required
  - Toggle persisted in `localStorage` (Settings > Analysis)
- [ ] `docs/adr/0030-onboarding-tag-suggestions.md`
  - Decision: suggestion library as i18n JSON (`de.json` / `en.json`),
    grouped by category; free-text input always available; selected tags
    written to the existing tag store at onboarding completion
- [ ] `docs/adr/0031-cycle-tracking-scope.md`
  - Decision: M4 introduces only a `cycle_day` optional integer field on
    `DayEntry` and a `cycle` tag category; no health claims, no algorithmic
    prediction; deeper integration deferred to M7 (Health Connect)
- [ ] Scope note in `docs/DESIGN_DOCUMENT.md` under the M4 section

---

## Sprint 1 — Entry Time Slots + Trend Smoothing

**Goal:** Two independent, low-risk improvements that deliver immediate user
value without touching onboarding or developer tooling.

### 1a — Entry Time Slots

**User story:** As a user I can optionally mark an entry as belonging to
morning, noon, or evening so that I can track intra-day patterns.

#### Backend

- [ ] Alembic migration: add `time_slot VARCHAR(10) NULL` to `day_entries`
- [ ] `TimeSlot` Python enum: `morning | noon | evening`
- [ ] `DayEntryCreate` / `DayEntryRead` Pydantic schemas updated
- [ ] `GET /api/v1/entries` and `GET /api/v1/entries/{id}` include `time_slot`
- [ ] `PATCH /api/v1/entries/{id}` accepts `time_slot`
- [ ] `docs/API.md` updated
- [ ] Unit tests: schema validation, migration round-trip

#### Frontend

- [ ] `EntryForm.svelte`: optional chip group (Morgens · Mittags · Abends),
      collapsed by default behind "+ More"; no chip selected = whole-day
- [ ] `EntrySheet.svelte`: same chip group in sheet mode
- [ ] i18n keys `entry.time_slot.*` in `de.json` / `en.json`
- [ ] Entry detail view shows time slot badge when set
- [ ] Component tests: chip selection, null default, form submission

### 1b — Trend Smoothing Toggle

**User story:** As a user I can switch between raw data and a smoothed
7-day moving average on the Trends chart to better read long-term patterns.

#### Frontend only — no backend changes

- [ ] `TrendsChart.svelte` / Mood tab: add `smoothed` boolean store
- [ ] Compute 7-day SMA in a `derivedSmoothed` Svelte store or inline util
- [ ] Toggle rendered as segmented control: `Raw | Smoothed`
- [ ] Toggle persisted via `devMode` pattern (localStorage key
      `cc_trend_smooth`)
- [ ] Smoothing only active for ranges ≥ 30 D; toggle hidden for 7 D
- [ ] i18n keys `trends.smoothing.*`
- [ ] Unit tests: SMA calculation edge cases (fewer points than window)

---

## Sprint 2 — Guided Onboarding + Cycle Tracking Groundwork

**Goal:** First-use experience that lets users build a meaningful tag set
before entering data; simultaneously introduce the data primitives for
cycle tracking.

### 2a — Guided Onboarding

**User story:** As a new user I am guided through a short onboarding flow
where I can pick tags from curated suggestions or enter custom ones, so
that my first entries are already well-structured.

#### Backend

- [ ] `GET /api/v1/onboarding/tag-suggestions` — returns suggestion library
      grouped by category from a static JSON asset (no DB write)
- [ ] `POST /api/v1/onboarding/complete` — marks user as onboarded
      (`onboarding_completed_at` timestamp on `User`)
- [ ] Alembic migration: `onboarding_completed_at TIMESTAMP NULL` on `users`
- [ ] Auth middleware: redirect unauthenticated `/onboarding` requests

#### Frontend

- [ ] `/onboarding` route (already hidden from nav per M3.5 Sprint 1)
      activated and linked from post-registration redirect
- [ ] Step 1: Welcome screen with CorrelCore value proposition (2–3 lines,
      no gamification copy)
- [ ] Step 2: Tag suggestion picker — category chips expand to tag chips;
      user can deselect any suggestion and type custom tags
- [ ] Step 3: Summary + "Start tracking" CTA that calls
      `POST /api/v1/onboarding/complete` and creates selected tags
- [ ] Progress indicator (3 dots, no percentage)
- [ ] Skip option on each step (skips remaining steps, marks onboarded)
- [ ] i18n keys `onboarding.*` in `de.json` / `en.json`
- [ ] `src/lib/data/tagSuggestions.ts` — typed suggestion library
      (categories: Work, Health, Social, Mood, Cycle, Custom)
- [ ] Component tests: step navigation, tag selection, skip, submission

### 2b — Cycle Tracking Groundwork

**User story:** As a user I can optionally log my cycle day on an entry
and use cycle-related tags so that patterns related to my cycle become
visible in Trends.

#### Backend

- [ ] Alembic migration: `cycle_day SMALLINT NULL` on `day_entries`
      (1–35 range; NULL = not tracked)
- [ ] `DayEntryCreate` / `DayEntryRead` updated
- [ ] `docs/API.md` updated
- [ ] Unit tests: range validation

#### Frontend

- [ ] `EntryForm.svelte`: optional numeric input for cycle day, behind
      "+ More", with range hint (1–35)
- [ ] Tag suggestion library includes `cycle` category
- [ ] Trends > Health tab: if `cycle_day` data exists, show cycle phase
      overlay on the mood chart (simple line, no algorithmic interpretation)
- [ ] i18n keys `entry.cycle_day.*`, `trends.cycle.*`
- [ ] No medical copy; framing: "Cycle day (optional)" with neutral hint text
- [ ] Component tests

---

## Sprint 3 — Developer Mode: Phase Switcher + Onboarding Mock

**Goal:** Extend the existing Dev Mode tooling so that every app phase
(onboarding, insight maturity stages, empty states) can be previewed
without real data.

**Existing foundation (M3.5 Sprint 7):** `devForceVisualizations` store
with `dev_force_viz` persistence; centralized mock entries, insights, and
trends.

### Deliverables

- [ ] Dev Mode panel (Settings > Developer) gains a **Phase Switcher**
      section with the following controls:
  - Insight maturity: `collecting (0–6d) | early (7–13d) | provisional
(14–29d) | robust (30+d)` — overrides `insight_maturity` in the
    insights store
  - Onboarding state: `completed | not completed` — toggles the
    onboarding redirect without touching the real user record
  - Entry count mock: numeric input (0–200) — controls the readiness
    meter display
- [ ] **Onboarding Preview** button opens the full `/onboarding` flow in
      a modal overlay so layouts can be reviewed without resetting the account
- [ ] Dev phase state stored in a dedicated `devPhase` Svelte store
      (in-memory only, not persisted across reloads)
- [ ] Disabling Dev Mode resets all phase overrides (consistent with
      existing `devForceVisualizations` reset behaviour)
- [ ] i18n keys `dev.phase.*`
- [ ] Component tests: phase switching, override propagation, reset

---

## Sprint 4 — PWA Hardening + Homescreen Install Prompt

**Goal:** Make the PWA install experience explicit and improve offline
resilience. Native Android widget is out of scope for M4.

### Deliverables

- [ ] `beforeinstallprompt` event captured in a Svelte store
      (`pwaInstallStore`)
- [ ] Install prompt banner on the Home screen: appears once, dismissible,
      stored as dismissed in `localStorage` (`cc_pwa_dismissed`)
- [ ] Service Worker (`service-worker.ts`): cache strategy reviewed;
      offline fallback page (`/offline`) added
- [ ] `manifest.webmanifest`: verify `display: standalone`, `start_url`,
      `theme_color` matches `--color-primary` in both themes
- [ ] `<meta name="apple-mobile-web-app-capable">` and related iOS PWA
      meta tags present
- [ ] PWA install tested on Android Chrome and iOS Safari
- [ ] `docs/features/PWA.md`: documents install flow, offline behaviour,
      and widget roadmap note (M11 via Android Glance API / TWA)
- [ ] i18n keys `pwa.*`
- [ ] Component tests: banner show/dismiss logic

---

## Sprint 5 — Visual QA, Docs & GitHub Closure

**Goal:** Validate all M4 changes at standard breakpoints, update
documentation, and close GitHub issues.

### Deliverables

- [ ] Rendered QA at 375 px, 768 px, and 1280 px (light + dark) — document
      in `docs/quality/M4_VISUAL_QA.md`
- [ ] Onboarding flow QA (all three steps, skip path, tag selection)
- [ ] Time slot chips QA (entry form + sheet + detail view)
- [ ] Trend smoothing toggle QA (30D and 90D ranges)
- [ ] Dev Mode phase switcher QA (all four maturity stages)
- [ ] PWA install prompt QA (Android Chrome + iOS Safari)
- [ ] `docs/FRONTEND.md` updated with onboarding route, time slots, cycle
      field, smoothing toggle, and phase switcher
- [ ] `docs/M4_SPRINT_STATUS.md` updated to Done for all sprints
- [ ] `CHANGELOG.md` updated under Unreleased
- [ ] GitHub issues for M4 closed or rescoped
- [ ] CI — Web green on final `main` commit

## Definition of Done

| Criterion                                        | Expected evidence                   |
| ------------------------------------------------ | ----------------------------------- |
| All sprint PRs / commits merged to `main`        | Sprints 0–5 on `main`               |
| All M4 issues closed or deliberately rescoped    | GitHub issue tracker                |
| `docs/FRONTEND.md` matches implemented UI        | Updated in Sprint 5                 |
| `docs/M4_SPRINT_STATUS.md` documents final state | All rows ✅ Done                    |
| `CHANGELOG.md` contains M4                       | Sprints 1–5 under Unreleased        |
| Local and GitHub CI gates green                  | `CI — Web` and `CI — API`           |
| Visual QA documented                             | `docs/quality/M4_VISUAL_QA.md`      |
| No gamification violations in visible UI copy    | `noGamificationCopy.test.ts` passes |
| ADRs 0028–0031 merged                            | `docs/adr/`                         |
