# ADR-0031: Cycle Tracking Groundwork Scope

Date: 2026-05-28

## Status

Accepted

## Context

Cycle-related context can be useful for personal reflection, but medical
interpretation, prediction, and platform health integrations require a larger
privacy and product review. M4 is scoped to quick wins and mobile/PWA
hardening, not full health-platform integration.

## Decision

M4 adds only neutral cycle groundwork:

- `entries.cycle_day` as nullable integer `1..35`
- `cycle` as an available tag category
- optional entry UI for cycle day behind `+ More`
- a neutral Health-tab display of cycle-day context when present

The app does not infer phases, predict dates, or make medical claims.

## Consequences

- Deeper cycle tracking remains deferred to a later health-integration
  milestone.
- The field is ready for export, analytics, and future UI without changing the
  current M4 exit criteria.
