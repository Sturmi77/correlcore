# ADR-0034: Onboarding Toggle for Cycle-specific Tags, Symptoms and Fields

Date: 2026-05-29

## Status

Accepted

## Context

M1 (Core Entry) and M3 (Insights v1) are complete. The onboarding flow
already features a tag-suggestion step (ADR-0030). M4 introduces the first
cycle data fields (`cycle_day`, bleeding level — see ADR-0031, ADR-0032).

Cycle-specific UI elements — symptom codes, entry fields, insight cards,
calendar overlays — are not relevant to all users. Displaying them by
default would:

1. Add friction to the core 60-second entry flow.
2. Surface health-related prompts to users who have not opted in.
3. Conflict with the Privacy-by-Design consent requirement for health data
   (ADR-0033 §7).

The question is: how should cycle tracking UI be activated, and where should
the toggle live?

## Decision

### 1. Onboarding placement

A dedicated step is added to the existing onboarding wizard **after** the
tag-suggestion step (ADR-0030) and **before** the first entry prompt:

```
Step 1: Welcome + quick tour
Step 2: Choose your core tags  ← ADR-0030
Step 3: Cycle tracking opt-in  ← NEW (this ADR)
Step 4: Create your first entry
```

The step displays:

- **Headline**: "Track your cycle alongside your daily entries?"
- **Body**: "When enabled, CorrelCore can show how your cycle phase relates
  to mood, energy, sleep, and more. All data stays on your server."
- **Two options**:
  - ✅ "Yes, enable cycle tracking" (non-default)
  - ○ "No thanks, skip for now"
- A subtle "You can change this anytime in Settings" note.

The default is **off** (`cycle_tracking_enabled = false`).

### 2. Settings availability

The toggle is also available in **Settings → Tracking → Cycle tracking**
at any time after onboarding. The toggle:

- **ON → OFF**: Hides all cycle-specific UI. Existing data is **preserved**
  (not deleted). A brief note explains: "Your cycle data is kept. You can
  re-enable tracking to see it again."
- **OFF → ON**: Re-shows all cycle-specific UI and any previously recorded
  data.

Deletion of cycle data is a separate action available at
**Settings → Privacy → Delete cycle data** (backed by ADR-0033 §6).

### 3. What the toggle controls (UI scope)

| UI element                               | Toggle OFF              | Toggle ON             |
| ---------------------------------------- | ----------------------- | --------------------- |
| `cycle_day` field in entry form          | Hidden (under `+ More`) | Visible in entry form |
| `cycle_bleeding_level` field             | Hidden                  | Visible               |
| Cycle symptom codes in symptom picker    | Hidden                  | Visible               |
| Cycle event buttons (period start, etc.) | Hidden                  | Visible               |
| Calendar cycle overlay (M5)              | Hidden                  | Visible               |
| Cycle-phase insight cards                | Hidden                  | Visible               |
| Health tab cycle section                 | Hidden                  | Visible               |

The `cycle_day` field remains accessible under `+ More` even when the
toggle is off (consistent with ADR-0031), so power users who bypass the
toggle can still log a cycle day manually.

### 4. Implementation

- The toggle state is stored as a user preference:
  `user_preferences.cycle_tracking_enabled: boolean`.
- The SvelteKit frontend reads this preference from the user profile store
  on load and applies it reactively via a Svelte store / context.
- No server-side feature flag is required; this is a pure client-side
  visibility decision. The API always accepts cycle fields regardless of
  the toggle state.
- The onboarding step is guarded: it is only shown on first login
  (onboarding not yet completed) or when the preference has never been set.

### 5. Re-triggering

Users who skipped the onboarding step and have never set the preference see
a **non-intrusive nudge** in the Health tab:

> "Want to track how your cycle affects your wellbeing?"
> [Enable cycle tracking]

This nudge is shown at most once per week and is permanently dismissible.

## Considered Alternatives

| Alternative                           | Reason rejected                                                              |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| Always show cycle fields, no toggle   | Adds friction for non-relevant users; violates health data consent principle |
| Feature flag server-side              | Overkill for a user preference; adds API round-trip on every page load       |
| Separate "Cycle" screen in navigation | Creates a competing entry flow and breaks the single-entry-per-day model     |
| Opt-out (on by default)               | Contradicts Privacy-by-Design consent requirement for health data            |

## Milestone Mapping

| Deliverable                                     | Milestone        |
| ----------------------------------------------- | ---------------- |
| `user_preferences.cycle_tracking_enabled` field | M4 (in progress) |
| Onboarding step 3 (cycle opt-in)                | M4               |
| Settings toggle + hide/show logic               | M4               |
| Health tab nudge card                           | M4               |
| Calendar overlay controlled by toggle           | M5               |
| Cycle insight cards controlled by toggle        | M5               |

## Consequences

- The onboarding wizard gains one additional step; the existing step order
  (ADR-0030) is preserved and this step is appended after it.
- The SvelteKit preference store is the single source of truth for this
  toggle; it must be loaded before any entry form renders.
- The M4 sprint must include the `user_preferences` API extension and the
  onboarding step before the cycle entry fields go live.
- This toggle pattern establishes a reusable precedent for future optional
  feature groups (e.g., sleep tracking, photo entries).
