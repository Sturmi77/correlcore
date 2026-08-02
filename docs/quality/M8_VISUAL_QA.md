# M8 Visual QA — Sleep & Health Connect

Last updated: 2026-08-02 · Milestone: M8 core (Sprints 1–5)

Manual visual QA checklist. Run at **375 px** and **768 px**, in **light and dark**.
Web parts are testable in any browser; Health Connect parts need the Android app.

## Entry form — Schlaf section (Sprint 1)

- [ ] `/entries` full mode shows a **Schlaf** section with a duration input and a quality select.
- [ ] Duration accepts 0–1440; out-of-range shows the range error; empty clears the value.
- [ ] Quality select shows "Nicht gesetzt" + 1–5 labels; selection persists after auto-save.
- [ ] Layout is clean at 375 px and 768 px, light + dark; umlauts render (Schlafqualität).
- [x] Verified in-browser during Sprint 1 (desktop + 375 px, no console errors).

## Insights — sleep↔mood (Sprint 2)

- [ ] With ≥15 paired sleep+mood days, a sleep↔mood correlation card appears in the feed.
- [ ] The statement reads as plain prose and ends with the "not a diagnosis" disclaimer.
- [ ] No sleep card appears when sleep data is sparse (< 15 paired days).

## Health Connect rationale + sync (Sprint 3/4) — Android app

- [ ] `/health-connect` shows: intro, the two data types (sleep + heart rate), the "only these two" note, and the four sections (what/why/on-device/control).
- [x] Rationale page renders on web build with the "Android only" status (verified in-browser).
- [ ] On device without server consent: page shows "grant consent first"; no permission sheet.
- [ ] After consent: **Grant Health Connect access** opens the OS sheet listing only Sleep + Heart rate.
- [ ] After permission: **Sync now** runs; result message shows ok / no_data as appropriate.
- [ ] The **sleep-sync toggle** persists (reload keeps state); off ⇒ Sync now disabled and import returns `sleep_sync_enabled: false`.
- [ ] Health Connect app → "See app permissions" launches the rationale page.
- [ ] Layout clean at 375/768 px, light + dark.

## Notes

- The native permission flow and on-device layout must be checked on a real device
  (Android 14 built-in HC; Android 13 install the HC app). See
  [`features/HEALTH_CONNECT.md`](../features/HEALTH_CONNECT.md) for the device build steps.
