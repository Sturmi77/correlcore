# ADR-0019 — Developer Mode Toggle in Settings

## Status

Accepted (2026-05-13)

## Context

ADR-0015 established the `/dev` route as a default-off diagnostic view accessible to authenticated and verified users. However, it did not define the UX mechanism for enabling this route. Currently the route exists but there is no user-facing toggle to activate it — users need to know the URL directly.

The `/dev` route is a diagnostic tool, not a product feature. It must not appear in the main navigation or count as a user-facing screen in the information architecture (ADR-0017).

## Decision

Developer mode is enabled via a **hidden tap sequence** in the Settings screen:

1. The app version string in the Settings footer (e.g., `v0.12.0 · build abc1234`) is a tappable element with no visible affordance.
2. After **7 consecutive taps within 3 seconds**, a brief toast notification appears: `"Developer mode enabled"` / `"Developer mode disabled"` (toggle).
3. The `dev_mode_enabled` boolean is persisted in `localStorage` (client-side only — no server round-trip, no user preference API call).
4. When `dev_mode_enabled === true`, a `DEVELOPER` section becomes visible at the bottom of the Settings page containing:
   - A `Developer mode` toggle (to disable again without the tap sequence)
   - A `Open developer view →` link to `/dev`
5. The `/dev` route itself remains guarded by `DEV_VIEW_ENABLED` (backend env flag, ADR-0015). If the backend flag is off, the frontend link leads to a "Dev view not available in this deployment" message.

### Why 7 taps (not a menu option or URL)

- Prevents casual users from accidentally discovering diagnostic screens
- Does not add visual clutter to the settings UI for the primary persona
- Pattern is established convention (Android Developer Options, various iOS debug menus)
- Does not require server-side feature flags for the toggle itself

### Why localStorage (not user_preferences)

- Dev mode is a per-device/per-browser diagnostic preference, not a user data preference
- Avoids a backend round-trip for a purely diagnostic toggle
- Acceptable data loss on storage clear (user simply taps 7× again)

## Consequences

- `settings/+page.svelte` gains a tappable version string element and dev mode section (Issue #165).
- A `devMode` store wrapping `localStorage` is added to `lib/stores/`.
- The `/dev` route gains a graceful "not available" state when the backend flag is off.
- ADR-0015 is extended by reference to this ADR for the UX mechanism.
- The `/dev` route does not appear in the bottom navigation bar or any user-facing sitemap.
