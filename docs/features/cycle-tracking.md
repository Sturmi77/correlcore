# Cycle Tracking — Feature Overview

> **2026-07-26 update:** The shipped form is the `cycle_day` metric (1–35) plus
> CYCLE tag category, now gated by an **opt-out toggle** `cycle_tracking_enabled`
> (user preference, migration `032`; ADR-0034 Stage 1). It is set on the last
> onboarding screen and re-toggleable under Settings → Cycle. Bleeding strength,
> cycle-specific symptoms, and phase inference remain deferred to [#547](https://github.com/Sturmi77/correlcore/issues/547).
>
> **Status**: Partially implemented (M4 in progress)
> **Relevant ADRs**: [ADR-0031](../adr/0031-cycle-tracking-scope.md) · [ADR-0032](../adr/0032-cycle-tracking-as-domain-extension.md) · [ADR-0033](../adr/0033-sensitive-health-data-handling-cycle-signals.md) · [ADR-0034](../adr/0034-onboarding-cycle-tracking-toggle.md)
> **Related ADRs**: [ADR-0008](../adr/0008-symptom-master-tabelle.md) · [ADR-0021](../adr/0021-insight-maturity-phases.md) · [ADR-0028](../adr/0028-entry-slot-model.md) · [ADR-0030](../adr/0030-onboarding-tag-suggestions.md)

## Purpose

Cycle tracking in CorrelCore allows users to record menstrual cycle context
alongside their daily entries — without turning CorrelCore into a dedicated
cycle app. The goal is to surface **cross-domain correlations**: how cycle
phase relates to sleep, mood, energy, headaches, productivity, and other
lifestyle signals already tracked in the system.

CorrelCore does **not** provide:

- Medical diagnoses or clinical interpretation
- Fertility tracking or contraception guidance
- Predictions with certainty claims

## Architecture Summary

Cycle tracking is a **domain extension** of the existing `entries` and
`insights` modules (ADR-0032). No separate module or screen is created.

```
DayEntry
  └─ cycle_day              (nullable int, 1–40)
  └─ cycle_bleeding_level   (nullable enum)
  └─ cycle_phase_reported   (nullable enum)
  └─ cycle_phase_inferred   (nullable enum, set by insight engine)
  └─ cycle_events           (list: period_start, ovulation_suspected, …)

SymptomEntry (existing, via ADR-0008)
  └─ category: "cycle"      (new category, hidden behind toggle)
     codes: cramps, bloating, breast_tenderness, pelvic_pain,
            back_pain_cycle, headache_cycle, skin_breakout,
            food_craving, libido_change, cervical_mucus

CycleSnapshot (derived, insight-engine-internal)
  └─ cycle_number, phase, day_in_cycle, next_period_window (±2 days)
```

## Opt-out Toggle

As shipped (Stage 1, 2026-07-26), cycle tracking is **on by default (opt-out)**:
`cycle_tracking_enabled` server-defaults to `true`. Users can turn it **off** on
the last onboarding screen, or at any time via **Settings → Cycle**. When off,
the `cycle_day` entry field is hidden. (The original ADR-0034 §1 proposed opt-in
/ default-off; the implemented reversal is recorded in that ADR's Decision note.)

See ADR-0034 for the full toggle specification, including what is shown/hidden
and the Settings-level deletion path.

## Data Privacy

Cycle data is classified as **Sensitive Health Data (SHD)** under GDPR
Article 9. Key rules (full spec in ADR-0033):

- SHD field values are **never logged** in application or error logs.
- A `sanitise_entry_for_log()` utility redacts SHD fields before any log output.
- Selective SHD deletion: `DELETE /api/v1/entries/cycle-data` clears cycle
  fields while preserving the base entry record.
- Play Store data safety form must declare cycle data as collected, encrypted,
  not shared, user-deletable (required for M11).

## Milestone Roadmap

| Milestone                 | Deliverables                                                                                                                                                                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M4** _(in progress)_    | `cycle_day` + `cycle_bleeding_level` fields; migration; onboarding toggle (ADR-0034); `user_preferences.cycle_tracking_enabled`; Settings toggle; Health tab nudge; `sanitise_entry_for_log()`; `DELETE /api/v1/entries/cycle-data` |
| **M5** _(Habits)_         | Cycle symptom taxonomy extension (ADR-0008); calendar overlay with cycle markers; basic cycle phase visualisation; first pattern-based insight rules (≥3 cycles)                                                                    |
| **M7** _(Insights v2)_    | Core analytics shipped (Lasso, lag, symptom L1/L2, tag clusters). Cycle×lifestyle deferred to **M7.1** — see sprint plan.                                                                                                           |
| **M8** _(Health Connect)_ | External cycle data import (Android Health Connect); cross-source cycle day reconciliation                                                                                                                                          |

## Insight Examples

All insights use template-based language with confidence levels (ADR-0018,
ADR-0021). Examples of valid output:

> 🔵 **Pattern detected** (medium confidence, 4 cycles)
> "Your logged headaches appear 1–2 days before your period starts in
> 3 of the last 4 cycles."

> 🟡 **Possible pattern** (low confidence, 2 cycles)
> "Sleep quality scores tend to be lower in your late luteal phase.
> More data needed for a reliable pattern."

> ⬜ **Not enough data**
> "Record at least 3 complete cycles to unlock cycle-based insights."

## Medical Disclaimer

Shown persistently in all cycle-related UI sections:

> _CorrelCore shows patterns in your own data. It does not provide medical
> advice, diagnoses, or fertility guidance. Consult a healthcare provider
> for medical questions._
