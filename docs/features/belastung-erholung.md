# Belastung & Erholung — Feature Overview

> **2026-09-19 (Phase 8):** Opt-in Layer-1 overlay for a named heuristic composite
> (“Belastungsmuster der letzten 14 Tage”). Ships with `work_context.other`,
> write-time covariates `logged_local_hour` / `inferred_period` (#892 Option 3),
> and preference `belastung_overlay_enabled` (default **false**).
>
> **Status**: Implemented as a thin overlay on existing entry data
> **Relevant issues**: [#875](https://github.com/Sturmi77/correlcore/issues/875) · [#892](https://github.com/Sturmi77/correlcore/issues/892)
> **Relevant ADR**: [ADR-0043](../adr/0043-insight-surface-layers.md) · [ADR-0016](../adr/0016-timeseries-split-ml-models.md)

## Purpose

Surface a cautious, user-owned summary of **load and recovery** patterns —
stress up, energy down, fatigue more often — compared with the prior fortnight.
The goal is orientation for people returning after illness, changing jobs, or
noticing sustained load. CorrelCore does **not** become a burnout product.

CorrelCore does **not** provide:

- Medical diagnoses or clinical inventories (MBI/CBI)
- Employer-facing reports or team views
- New required entry fields or a parallel burnout information architecture

## Architecture Summary

This is a **thin overlay** on existing `entries`, tags, and symptoms. No new
persistenz field on the day entry for “Belastung” itself.

```
user_preferences.belastung_overlay_enabled   (opt-in, default false)
  └─ gated by analytics_enabled (master switch)

entries
  └─ stress / energy (existing)
  └─ work_context (+ other)               # recovery / life context
  └─ logged_local_hour / inferred_period  # #892 Option 3; slot stays day

insight_type = belastung_pattern
  └─ payload: dual-denominator fatigue & recovery counts, slopes, heuristic flag
```

Reuse, do not invent tags:

| Signal            | Source                                                        |
| ----------------- | ------------------------------------------------------------- |
| Overtime-like     | tag `work_intense`                                            |
| Recovery day      | `work_context` in vacation / weekend / other / sick           |
| Achievement       | tag `achievement` (#890)                                      |
| After-hours write | `inferred_period = after_hours` (first log after 22:00 local) |
| Fatigue           | default symptom `fatigue`                                     |

## Opt-in Toggle

Unlike cycle tracking (opt-out / default on), Belastung is **opt-in / default
off**. Users enable it under **Settings → Data → Load & recovery**. When off,
no composite is generated and the Layer-1 overlay is hidden. Turning analysis
off also suppresses generation.

## Write-time covariates (#892 Option 3)

On `POST /entries?tz=<IANA>`, the server stores:

- `logged_local_hour` — hour 0–23 in the client zone (fallback UTC)
- `inferred_period` — `morning` | `daytime` | `evening` | `after_hours`

`entries.slot` remains `day`. Options that write morning/noon/evening into
`slot` are rejected (unique constraint risk + streak breakage). Write time is a
**covariate of `entry_date`**, never a time index (ADR-0016). Export includes
both fields; account delete cascades with the entry row.

## Language & framing

- Prefer “load / recovery / pattern / hint” — never clinical burnout labels in UI
- Always mark the composite as a **heuristic**
- Disclaimer includes the guardrail: data stays with the user, **never with an employer**
- Two CTAs open Layer 2 (`/insights/signal/[id]`) — work intensity and sleep/next-day

## Landing surface

Mockup E5: optional card on Insights Layer 1 (not a ninth `insight_sections`
key). Settings remains the on/off switch.

## Privacy

Same account boundary as other insights. Scatter/day-level detail on Layer 2
follows the Phase 7 screenshot caution. No third-party health cloud for this
overlay.
