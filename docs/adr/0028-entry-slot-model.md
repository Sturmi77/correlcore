# ADR-0028: Entry Slot Model for M4

Date: 2026-05-28

## Status

Accepted

## Context

The backend already stores entry slots in `entries.slot` with the values
`day`, `morning`, `noon`, and `evening`. Earlier M4 planning mentioned a new
`time_slot` field, but that would duplicate the existing model and migration
history.

## Decision

M4 keeps `entries.slot` as the canonical time-slot field. The default `day`
continues to mean whole-day entry. `EntryUpdate` accepts `slot` so existing
entries can move between whole-day and intra-day slots.

Slot changes can collide with the existing per-user/date/slot uniqueness
constraint. The API maps that database conflict to HTTP `409`.

## Consequences

- No slot migration is required for M4.
- API clients use one stable field, `slot`, for create, read, update, and delta
  requests.
- Future slot analytics can build on the existing uniqueness invariant.
