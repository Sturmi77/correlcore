# ADR-0029: Client-Side Trend Smoothing

Date: 2026-05-28

## Status

Accepted

## Context

The M4 quick-win scope asks for a readable mood trend without adding backend
aggregation endpoints. Existing `/entries/stats/timeseries` responses already
contain daily or bucketed averages for mood, energy, and stress.

## Decision

The web client computes a 7-point trailing simple moving average for the mood
trend view. The toggle is rendered as `Raw | Smoothed`, hidden for the 7-day
range, and persisted in `localStorage` under `cc_trend_smooth`.

Null metric gaps are ignored within the moving window. If a window has no value
for a metric, the smoothed value remains `null`.

## Consequences

- No backend schema or endpoint change is required.
- Users can switch between original data and a softer trend for 30-day and
  longer ranges.
- The implementation remains descriptive and does not infer causality.
