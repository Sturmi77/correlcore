# ADR-0032: Cycle Tracking as Domain Extension of Entries and Insights

Date: 2026-05-29

## Status

Accepted

## Context

M1 (Core Entry), M2 (Visualisation), and M3 (Insights v1) are completed.
The existing architecture provides:

- A flexible `DayEntry` model with optional fields and a tag/symptom taxonomy
  (ADR-0008).
- A rule-based insight engine with confidence levels (ADR-0021).
- An entry-slot model for main entry + optional sub-slots (ADR-0028).
- An onboarding tag-suggestion step (ADR-0030).
- A minimal cycle groundwork field `cycle_day` already merged in M4
  preparation (ADR-0031).

User research and the competitive analysis in `docs/MARKET_ANALYSIS.md`
indicate that menstrual cycle context is one of the most requested
cross-domain correlation signals: users want to understand how their
physical cycle phase relates to sleep quality, mood, energy, headaches,
productivity, and social energy — **not** to receive medical diagnostics
or fertility predictions.

The question is: do we build cycle tracking as a separate platform module,
or extend the existing domain model?

## Decision

Cycle tracking is implemented as a **domain extension of `entries` and
`insights`**, not as a standalone module or a separate application feature.

Concrete consequences of this decision:

### 1. Data Model (backend)

The `DayEntry` model in `backend/` is extended with optional nullable fields:

```python
# Cycle signals — all nullable, not required
cycle_day: int | None = None                        # 1–40, user-reported or computed
cycle_bleeding_level: BleedingLevel | None = None   # enum: none|spotting|light|medium|heavy
cycle_phase_reported: CyclePhase | None = None      # enum: menstrual|follicular|ovulatory|luteal
cycle_phase_inferred: CyclePhase | None = None      # derived by insight engine
cycle_events: list[CycleEvent] = []                 # period_start, ovulation_suspected, etc.
```

A lightweight derived entity `CycleSnapshot` is computed and cached by the
insight engine for use in trend calculations. It is **never** the primary
record — the `DayEntry` remains the single source of truth.

### 2. Symptom Taxonomy (shared-types)

Cycle-adjacent symptom codes are added to the existing symptom master table
(ADR-0008) under a new category `cycle`:

```
cramps, bloating, breast_tenderness, pelvic_pain, back_pain_cycle,
headache_cycle, skin_breakout, food_craving, libido_change, cervical_mucus
```

These are visible **only** when cycle tracking is enabled (see ADR-0034).
The taxonomy structure is unchanged.

### 3. Insights (rule engine)

New rule types are added to the existing rule-based engine:

- **Pattern rules**: "Headache frequency peaks on days N±1 before
  `period_start`" — requires ≥ 3 completed cycles as minimum dataset.
- **Correlation rules**: Cycle phase vs. sleep quality, mood, energy score.
- **Forecast window**: Next likely period window (±2 days), shown only when
  ≥ 3 cycles are recorded with confidence annotation.

All outputs follow ADR-0018 (confidence visualisation): observations and
patterns are clearly labelled, no causal language, no medical claims.

### 4. Module structure

No new top-level module is created. The implementation lives inside the
existing feature boundaries:

```
backend/
  app/modules/entries/          # DayEntry model extension, DTOs, migrations
  app/modules/insights/         # CycleSnapshot, cycle-specific rule files

apps/web/src/features/entries/  # Cycle input components (behind toggle)
apps/web/src/features/insights/ # Cycle-aware insight cards

packages/shared-types/
  src/cycle.ts                  # Enums: BleedingLevel, CyclePhase, CycleEvent
  src/symptoms.ts               # Extended with cycle symptom codes
```

A dedicated `cycle/` subdirectory is added **within** `entries/` only if the
file count exceeds 6 files; otherwise cycle files are co-located with the
existing entry feature code.

## Considered Alternatives

| Alternative | Reason rejected |
|---|---|
| Standalone `cycle` module at top-level | Breaks the existing domain structure; creates parallel routing, duplicates data access patterns |
| Separate "Cycle" screen in navigation | Violates the single-source-of-truth entry model; creates two competing data entry flows |
| Third-party cycle tracking SDK | Incompatible with Privacy-by-Design and self-hosting principles |

## Milestone Mapping

| Deliverable | Milestone |
|---|---|
| `cycle_day`, `cycle_bleeding_level` fields, migration | M4 (in progress) |
| Cycle symptom taxonomy extension | M4 |
| Onboarding toggle (see ADR-0034) | M4 |
| Calendar overlay with cycle markers | M5 |
| Rule-based cycle pattern insights | M5 |
| Cycle × lifestyle correlations | M8 (Insights v2) |
| External health imports (cycle data) | M7 (Health Connect) |

## Consequences

- The existing entry, insight, and visualisation architecture is preserved
  without structural changes.
- Sprint sequencing for M4 and M5 must respect the "no parallel development"
  rule: cycle data model is completed before UI; UI is completed before
  insight rules referencing it.
- The `CycleSnapshot` derived entity must never be exposed directly via the
  public API; it is an internal insight-engine artefact.
- Competitively, this positions CorrelCore ahead of apps like Daylio and
  Bearable in cross-domain cycle correlations without becoming a dedicated
  cycle app.
