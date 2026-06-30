# ADR-0030: Guided Onboarding Tag Suggestions

Date: 2026-05-28

## Status

Accepted

## Context

New users benefit from a small curated tag set, but CorrelCore must avoid
writing duplicate user tags or forcing a fixed taxonomy. The existing tag model
already supports default tags and user-owned custom tags with slug uniqueness.

## Decision

M4 introduces `/api/v1/onboarding/tag-suggestions` for grouped static
suggestions and `/api/v1/onboarding/complete` for finalizing onboarding.

Selected suggestions and free-text inputs are stored as user custom tags. The
completion service is idempotent by slug: an existing visible default or custom
tag is reused instead of producing a conflict. Completion sets the existing
preferences `onboarding_retro_completed=true` and
`onboarding_profile_completed=true`.

## Amendment (2026-06-30) — Tags in first entry (O-06)

Tag suggestions move from the default `/onboarding` wizard into the first
`EntrySheet` on Home. `/onboarding` redirects to `/?openEntry=1`; the full
three-step wizard remains at `/onboarding?preview=1` for QA and regression.

`POST /api/v1/onboarding/complete` is still called on the first autosave when
onboarding tag hints are shown, preserving idempotent slug handling and
`onboarding_retro_completed` semantics.

## Consequences

- No new user-level onboarding timestamp is added in M4.
- Old `/onboarding/retro` and `/onboarding/profile` deep links can remain.
- Custom tags created during onboarding use the same lifecycle as tags created
  in Settings.
